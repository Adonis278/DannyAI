"""
Amazon Transcribe handler for Danny AI.
Converts speech to text with real-time streaming support.

Two modes:
  1. Batch — transcribe an S3 audio file (post-call analysis).
  2. Streaming — real-time transcription from a live audio feed
     (Kinesis Video Streams → this handler → Strands agent).

The streaming path uses the amazon-transcribe SDK which manages
WebSocket connections to the Transcribe Streaming API.
"""

import boto3
import asyncio
import logging
from typing import Optional, AsyncGenerator, Callable, Awaitable
import os

from ..config import get_config

logger = logging.getLogger(__name__)


class TranscribeHandler:
    """Handles speech-to-text using Amazon Transcribe (batch mode)."""

    def __init__(self):
        self.config = get_config()

        self.client = boto3.client(
            "transcribe",
            region_name=self.config.aws.region,
            aws_access_key_id=self.config.aws.access_key_id or None,
            aws_secret_access_key=self.config.aws.secret_access_key or None,
        )

        # Transcription settings
        self.language_code = "en-US"
        self.sample_rate = 8000  # Standard telephony sample rate
        self.media_encoding = "pcm"  # PCM for phone audio

    async def transcribe_audio_file(
        self,
        audio_uri: str,
        job_name: str,
        language_code: Optional[str] = None,
    ) -> dict:
        """
        Start a batch transcription job for an S3 audio file.

        Args:
            audio_uri: S3 URI of the audio file (s3://bucket/key)
            job_name: Unique name for this transcription job
            language_code: Optional language override

        Returns:
            Transcription job response
        """
        response = self.client.start_transcription_job(
            TranscriptionJobName=job_name,
            LanguageCode=language_code or self.language_code,
            Media={"MediaFileUri": audio_uri},
            Settings={"ShowSpeakerLabels": True, "MaxSpeakerLabels": 2},
        )
        return response

    async def get_transcription_result(self, job_name: str) -> Optional[str]:
        """
        Poll for the result of a batch transcription job.

        Returns:
            Transcribed text, or None if still in progress.
        """
        response = self.client.get_transcription_job(
            TranscriptionJobName=job_name
        )

        status = response["TranscriptionJob"]["TranscriptionJobStatus"]

        if status == "COMPLETED":
            import httpx

            result_uri = response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
            async with httpx.AsyncClient() as client:
                result = await client.get(result_uri)
                data = result.json()
                return data["results"]["transcripts"][0]["transcript"]
        elif status == "FAILED":
            raise Exception(
                f"Transcription failed: {response['TranscriptionJob'].get('FailureReason')}"
            )

        return None  # Still in progress

    def set_language(self, language_code: str):
        """Set the transcription language."""
        self.language_code = language_code


class StreamingTranscribeHandler:
    """
    Handles real-time streaming transcription.

    Used for live phone conversations via KVS or direct microphone input.
    Wraps the `amazon-transcribe` SDK which uses HTTP/2 WebSocket streaming.

    Usage:
        handler = StreamingTranscribeHandler()
        await handler.transcribe_stream(
            audio_stream=kvs_consumer.async_audio_stream(),
            on_transcript=my_callback,           # called with final transcripts
            on_partial=my_partial_callback,       # called with interim results
        )
    """

    def __init__(
        self,
        *,
        language_code: str = "en-US",
        sample_rate: int = 8000,
        region: Optional[str] = None,
    ):
        self.config = get_config()
        self.region = region or self.config.aws.region
        self.language_code = language_code
        self.sample_rate = sample_rate

    async def transcribe_stream(
        self,
        audio_stream: AsyncGenerator[bytes, None],
        on_transcript: Callable[[str], Awaitable[None]],
        on_partial: Optional[Callable[[str], Awaitable[None]]] = None,
    ):
        """
        Real-time streaming transcription.

        Args:
            audio_stream: Async generator yielding raw PCM audio chunks.
            on_transcript: Awaitable callback fired with each *final* transcript.
            on_partial: Optional callback fired with interim (partial) transcripts.
        """
        try:
            from amazon_transcribe.client import TranscribeStreamingClient
            from amazon_transcribe.handlers import TranscriptResultStreamHandler
            from amazon_transcribe.model import TranscriptEvent
        except ImportError:
            logger.error(
                "amazon-transcribe SDK not installed. "
                "Run: pip install amazon-transcribe"
            )
            raise

        # ----------------------------------------------------------
        # Custom event handler that routes transcripts to callbacks
        # ----------------------------------------------------------
        class _EventHandler(TranscriptResultStreamHandler):
            def __init__(self, output_stream, final_cb, partial_cb):
                super().__init__(output_stream)
                self._final_cb = final_cb
                self._partial_cb = partial_cb

            async def handle_transcript_event(
                self, transcript_event: TranscriptEvent
            ):
                for result in transcript_event.transcript.results:
                    for alt in result.alternatives:
                        text = alt.transcript.strip()
                        if not text:
                            continue
                        if result.is_partial:
                            if self._partial_cb:
                                await self._partial_cb(text)
                        else:
                            await self._final_cb(text)

        # ----------------------------------------------------------
        # Set up and run the streaming session
        # ----------------------------------------------------------
        client = TranscribeStreamingClient(region=self.region)

        stream = await client.start_stream_transcription(
            language_code=self.language_code,
            media_sample_rate_hz=self.sample_rate,
            media_encoding="pcm",
        )

        handler = _EventHandler(stream.output_stream, on_transcript, on_partial)

        async def _send_audio():
            try:
                async for chunk in audio_stream:
                    await stream.input_stream.send_audio_event(audio_chunk=chunk)
            finally:
                await stream.input_stream.end_stream()
                logger.debug("Transcribe audio stream ended")

        logger.info(
            "Transcribe streaming started — lang=%s, rate=%dHz",
            self.language_code,
            self.sample_rate,
        )
        await asyncio.gather(_send_audio(), handler.handle_events())
        logger.info("Transcribe streaming completed")

    async def transcribe_stream_sync_fallback(
        self,
        audio_chunks: list[bytes],
        on_transcript: Callable[[str], Awaitable[None]],
    ):
        """
        Fallback: feed pre-collected audio chunks through the streaming API.
        Useful for testing without a live KVS stream.
        """
        async def _gen():
            for chunk in audio_chunks:
                yield chunk
                await asyncio.sleep(0.01)  # Small delay to avoid back-pressure

        await self.transcribe_stream(_gen(), on_transcript)

    def set_language(self, language_code: str):
        """Set the transcription language."""
        self.language_code = language_code


# ---------------------------------------------------------------------------
# Singleton instances
# ---------------------------------------------------------------------------
_transcribe_handler: Optional[TranscribeHandler] = None
_streaming_handler: Optional[StreamingTranscribeHandler] = None


def get_transcribe_handler() -> TranscribeHandler:
    """Get the singleton Transcribe handler."""
    global _transcribe_handler
    if _transcribe_handler is None:
        _transcribe_handler = TranscribeHandler()
    return _transcribe_handler


def get_streaming_transcribe_handler(**kwargs) -> StreamingTranscribeHandler:
    """Get the singleton streaming Transcribe handler."""
    global _streaming_handler
    if _streaming_handler is None:
        _streaming_handler = StreamingTranscribeHandler(**kwargs)
    return _streaming_handler
