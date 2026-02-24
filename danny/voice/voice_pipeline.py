"""
Voice Pipeline Orchestrator for Danny AI.

This is the central engine that ties the full AWS voice stack together:

    Amazon Connect  ──►  KVS (live audio)
                                │
                    KVSConsumer ─┘
                                │
                    StreamingTranscribeHandler  ──►  text
                                                      │
                            Strands Agent  ◄──────────┘
                                │
                    PollyHandler  ◄──  response text
                                │
                    Connect (playback)  ◄──  audio bytes

Additionally:
  • DynamoDB stores session state & consent flags per contact.
  • S3 stores encrypted recordings and transcripts.
  • The pipeline manages turn-taking: caller speaks → Danny responds → repeat.
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data objects
# ---------------------------------------------------------------------------

@dataclass
class PipelineConfig:
    """Tunable pipeline parameters."""

    language_code: str = "en-US"
    sample_rate: int = 8000
    polly_voice: str = "Joanna"
    polly_engine: str = "neural"
    polly_output_format: str = "pcm"  # PCM for Connect playback
    # Silence-based turn detection
    silence_threshold_ms: int = 1500  # ms of silence before treating as end-of-turn
    max_turn_duration_s: float = 30.0  # max seconds per caller turn
    # Limits
    max_response_chars: int = 3000
    max_session_duration_s: float = 600.0  # 10 min


@dataclass
class PipelineSession:
    """Runtime state for a single call."""

    session_id: str
    contact_id: str
    caller_number: str = ""
    language: str = "en-US"
    turns: list = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    ended: bool = False
    transfer_requested: bool = False
    consent_given: Optional[bool] = None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class VoicePipeline:
    """
    Orchestrates a full voice call through the AWS stack.

    Lifecycle:
        1. ``start(contact_id, stream_arn, ...)`` — Begin processing a call.
        2. Internally loops: KVS → Transcribe → Agent → Polly → callback.
        3. ``stop()`` — Tear down resources.
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self._session: Optional[PipelineSession] = None
        self._kvs_consumer = None
        self._transcribe = None
        self._stopped = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def start(
        self,
        contact_id: str,
        stream_arn: str,
        caller_number: str = "",
        *,
        on_response_audio: Optional[Callable[[bytes], Awaitable[None]]] = None,
        on_response_text: Optional[Callable[[str], Awaitable[None]]] = None,
        on_transcript: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        """
        Start the full voice pipeline for a live call.

        Args:
            contact_id: Amazon Connect contact ID.
            stream_arn: KVS stream ARN for caller audio.
            caller_number: Caller's phone number.
            on_response_audio: Optional callback with Polly PCM audio for playback.
            on_response_text: Optional callback with Danny's text response.
            on_transcript: Optional callback with final caller transcript segments.
        """
        session_id = str(uuid.uuid4())
        self._session = PipelineSession(
            session_id=session_id,
            contact_id=contact_id,
            caller_number=caller_number,
            language=self.config.language_code,
        )

        logger.info(
            "Voice pipeline starting — contact=%s session=%s",
            contact_id,
            session_id,
        )

        # ---- Persistence: create session record ----
        try:
            from ..persistence import get_dynamodb_store

            db = get_dynamodb_store()
            db.save_session(
                session_id=session_id,
                data={
                    "contact_id": contact_id,
                    "caller_number": caller_number,
                    "language": self.config.language_code,
                    "status": "active",
                },
            )
            db.log_call_event(
                contact_id=contact_id,
                event_type="call_started",
                data={"caller": caller_number, "session_id": session_id},
            )
        except Exception as e:
            logger.warning("Persistence unavailable (non-fatal): %s", e)

        # ---- Set up KVS consumer ----
        from .kvs_consumer import KVSConsumer

        self._kvs_consumer = KVSConsumer(
            stream_arn,
            region=None,  # uses default from env
        )

        # ---- Set up streaming Transcribe ----
        from .transcribe_handler import StreamingTranscribeHandler

        self._transcribe = StreamingTranscribeHandler(
            language_code=self.config.language_code,
            sample_rate=self.config.sample_rate,
        )

        # ---- Run the turn loop ----
        await self._run_turn_loop(
            on_response_audio=on_response_audio,
            on_response_text=on_response_text,
            on_transcript=on_transcript,
        )

    async def stop(self):
        """Stop the pipeline gracefully."""
        self._stopped = True

        if self._kvs_consumer:
            self._kvs_consumer.stop()

        if self._session and not self._session.ended:
            self._session.ended = True

            # ---- Persist end of call ----
            try:
                from ..persistence import get_dynamodb_store, get_s3_store

                db = get_dynamodb_store()
                s3 = get_s3_store()

                db.update_session(
                    self._session.session_id,
                    updates={"status": "ended"},
                )
                db.log_call_event(
                    contact_id=self._session.contact_id,
                    event_type="call_ended",
                    data={
                        "session_id": self._session.session_id,
                        "turns": len(self._session.turns),
                        "transfer": self._session.transfer_requested,
                    },
                )

                # Save full transcript to S3
                transcript_text = self._build_transcript()
                if transcript_text:
                    s3.save_transcript(
                        session_id=self._session.session_id,
                        transcript=transcript_text,
                    )
            except Exception as e:
                logger.warning("Persistence cleanup error (non-fatal): %s", e)

        logger.info("Voice pipeline stopped — session=%s", self._session.session_id if self._session else "?")

    # ------------------------------------------------------------------
    # Turn-based conversation loop
    # ------------------------------------------------------------------

    async def _run_turn_loop(
        self,
        on_response_audio: Optional[Callable[[bytes], Awaitable[None]]] = None,
        on_response_text: Optional[Callable[[str], Awaitable[None]]] = None,
        on_transcript: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        """
        Core conversation loop.

        The Transcribe handler runs continuously while the KVS stream is alive.
        Each *final* transcript segment is treated as the end of a caller turn.
        Danny processes the text and responds via Polly.
        """
        collected_text: list[str] = []
        last_final_time: float = time.time()
        pending_response: asyncio.Event = asyncio.Event()
        response_lock: asyncio.Lock = asyncio.Lock()

        # -- Callbacks wired into Transcribe --
        async def _on_final(text: str):
            """Called for each final transcript from Transcribe."""
            nonlocal last_final_time
            last_final_time = time.time()
            collected_text.append(text)

            if on_transcript:
                await on_transcript(text)

            # Signal that we have new text
            pending_response.set()

        async def _on_partial(text: str):
            """Called for interim/partial transcripts."""
            pass  # Can be used for UI updates

        # ---- Launch transcription in background ----
        transcribe_task = asyncio.create_task(
            self._transcribe.transcribe_stream(
                audio_stream=self._kvs_consumer.async_audio_stream(
                    chunk_duration_ms=100,
                    sample_rate=self.config.sample_rate,
                ),
                on_transcript=_on_final,
                on_partial=_on_partial,
            )
        )

        # ---- Send initial greeting ----
        try:
            greeting = await self._get_agent_response(
                "A patient is calling. Please greet them warmly and ask how you can help."
                + (f" Their phone number is {self._session.caller_number}." if self._session.caller_number else "")
            )

            if greeting and not self._stopped:
                self._session.turns.append({"role": "assistant", "text": greeting})

                if on_response_text:
                    await on_response_text(greeting)

                audio = await self._synthesize(greeting)
                if audio and on_response_audio:
                    await on_response_audio(audio)
        except Exception as e:
            logger.error("Greeting failed: %s", e)

        # ---- Turn processing loop ----
        try:
            while not self._stopped and not self._session.ended:
                # Wait for the caller to say something
                try:
                    await asyncio.wait_for(
                        pending_response.wait(),
                        timeout=self.config.silence_threshold_ms / 1000 * 2,
                    )
                except asyncio.TimeoutError:
                    # Check if transcribe task ended (caller hung up)
                    if transcribe_task.done():
                        break
                    continue

                pending_response.clear()

                # Small debounce: wait a beat for more speech
                await asyncio.sleep(self.config.silence_threshold_ms / 1000)

                # Gather accumulated text
                async with response_lock:
                    if not collected_text:
                        continue

                    caller_text = " ".join(collected_text)
                    collected_text.clear()

                if not caller_text.strip():
                    continue

                logger.info("Caller said: %s", caller_text[:120])
                self._session.turns.append({"role": "user", "text": caller_text})

                # ---- Process through agent ----
                response = await self._get_agent_response(caller_text)
                if not response or self._stopped:
                    continue

                # Check for transfer request
                if "[TRANSFER_REQUESTED]" in response:
                    response = response.split("[TRANSFER_REQUESTED]")[0].strip()
                    self._session.transfer_requested = True
                    if not response:
                        response = "Let me transfer you to a staff member who can help."

                self._session.turns.append({"role": "assistant", "text": response})

                if on_response_text:
                    await on_response_text(response)

                # ---- Synthesize and play back ----
                audio = await self._synthesize(response)
                if audio and on_response_audio:
                    await on_response_audio(audio)

                # If transfer requested, end pipeline
                if self._session.transfer_requested:
                    break

                # Session time guard
                elapsed = time.time() - self._session.started_at
                if elapsed > self.config.max_session_duration_s:
                    logger.info("Session time limit reached")
                    break

        except asyncio.CancelledError:
            logger.info("Pipeline cancelled")
        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)
        finally:
            # Clean up transcribe
            if not transcribe_task.done():
                transcribe_task.cancel()
                try:
                    await transcribe_task
                except (asyncio.CancelledError, Exception):
                    pass

            await self.stop()

    # ------------------------------------------------------------------
    # Agent integration
    # ------------------------------------------------------------------

    async def _get_agent_response(self, user_text: str) -> Optional[str]:
        """
        Send text to the Strands agent and return the response.
        Runs the synchronous agent call in a thread executor.
        """
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, self._call_agent_sync, user_text
            )
            return response
        except Exception as e:
            logger.error("Agent error: %s", e)
            return "I'm sorry, I'm having some difficulty. Could you please repeat that?"

    def _call_agent_sync(self, user_text: str) -> str:
        """Synchronous wrapper to call the Strands agent."""
        from ..strands_agent import get_danny_agent

        agent = get_danny_agent()
        response = agent(user_text)

        # Extract text from AgentResult
        response_text = self._extract_response_text(response)

        # Clean for speech
        response_text = self._clean_for_speech(response_text)

        # Enforce length limit
        if len(response_text) > self.config.max_response_chars:
            response_text = response_text[: self.config.max_response_chars - 50]
            response_text += "... Would you like me to continue?"

        return response_text

    @staticmethod
    def _extract_response_text(response) -> str:
        """Extract plain text from a Strands AgentResult."""
        text = ""
        if hasattr(response, "message") and response.message:
            msg = response.message
            if isinstance(msg, dict):
                content = msg.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and "text" in item:
                            text += item["text"]
                elif isinstance(content, str):
                    text = content
            elif hasattr(msg, "content"):
                text = str(msg.content)
            else:
                text = str(msg)
        elif hasattr(response, "content"):
            text = str(response.content)
        else:
            text = str(response)

        # Handle stray dict repr
        if text.startswith("{'role':"):
            try:
                parsed = eval(text)
                content = parsed.get("content", [])
                if isinstance(content, list) and content:
                    text = content[0].get("text", text)
            except Exception:
                pass

        return text

    @staticmethod
    def _clean_for_speech(text: str) -> str:
        """Strip markdown and other artifacts for TTS output."""
        import re

        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # bold
        text = re.sub(r"\*([^*]+)\*", r"\1", text)  # italic
        text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)  # headers
        text = re.sub(r"^[-*]\s*", "", text, flags=re.MULTILINE)  # bullets
        text = re.sub(r"\n\s*\n", "\n", text)  # double newlines
        text = re.sub(r"```[^`]*```", "", text)  # code blocks
        text = re.sub(r"`([^`]+)`", r"\1", text)  # inline code
        return text.strip()

    # ------------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------------

    async def _synthesize(self, text: str) -> Optional[bytes]:
        """Synthesize text to speech using Polly."""
        if not text.strip():
            return None

        try:
            loop = asyncio.get_event_loop()
            audio = await loop.run_in_executor(None, self._polly_sync, text)
            return audio
        except Exception as e:
            logger.error("Polly synthesis error: %s", e)
            return None

    def _polly_sync(self, text: str) -> bytes:
        """Synchronous Polly call."""
        from .polly_handler import PollyHandler

        handler = PollyHandler()
        handler.set_voice(self.config.polly_voice)
        handler.engine = self.config.polly_engine

        return handler.synthesize_speech(
            text,
            output_format=self.config.polly_output_format,
            voice_id=self.config.polly_voice,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_transcript(self) -> str:
        """Build a human-readable transcript from the turn list."""
        if not self._session or not self._session.turns:
            return ""

        lines = []
        for turn in self._session.turns:
            role = "Caller" if turn["role"] == "user" else "Danny"
            lines.append(f"{role}: {turn['text']}")

        return "\n\n".join(lines)

    @property
    def session(self) -> Optional[PipelineSession]:
        return self._session


# ---------------------------------------------------------------------------
# Lambda-friendly entry point
# ---------------------------------------------------------------------------

async def handle_connect_call(
    contact_id: str,
    stream_arn: str,
    caller_number: str = "",
    *,
    config: Optional[PipelineConfig] = None,
    on_response_audio: Optional[Callable[[bytes], Awaitable[None]]] = None,
    on_response_text: Optional[Callable[[str], Awaitable[None]]] = None,
):
    """
    High-level entry point for processing a Connect call.

    This can be invoked from a Lambda handler or any other execution context.
    """
    pipeline = VoicePipeline(config=config)
    try:
        await pipeline.start(
            contact_id=contact_id,
            stream_arn=stream_arn,
            caller_number=caller_number,
            on_response_audio=on_response_audio,
            on_response_text=on_response_text,
        )
    finally:
        await pipeline.stop()

    return pipeline.session
