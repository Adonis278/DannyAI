"""
Danny AI - FastAPI Web Server

Exposes the Strands agent as a REST API so the React website
can send messages and get real AI responses with live Calendly data.
"""

import os
import re
import sys
import uuid
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Ensure danny package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("danny_api")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Danny AI API",
    description="REST API for the Danny dental AI assistant (Strands agent)",
    version="1.0.0",
)

# CORS — allow the React dev server and any local origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*",  # Remove in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory session store  (swap for DynamoDB / Redis in production)
# ---------------------------------------------------------------------------
# Each session maps to a Strands Agent instance so conversation history
# is maintained across turns.
from danny.strands_agent import create_danny_agent

_sessions: dict[str, dict] = {}

MAX_SESSIONS = 200  # cap to avoid memory leaks in demo


def _get_or_create_session(session_id: Optional[str] = None) -> tuple[str, object]:
    """Return (session_id, agent).  Creates a new session when needed."""
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]["agent"]

    # Evict oldest if we hit the cap
    if len(_sessions) >= MAX_SESSIONS:
        oldest = next(iter(_sessions))
        del _sessions[oldest]

    sid = session_id or str(uuid.uuid4())
    agent = create_danny_agent(
        use_bedrock=os.getenv("USE_BEDROCK", "false").lower() == "true",
        quiet=True,
    )
    _sessions[sid] = {"agent": agent}
    logger.info("Created new session %s  (total sessions: %d)", sid, len(_sessions))
    return sid, agent


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    transfer_requested: bool = False


class HealthResponse(BaseModel):
    status: str
    agent: str
    calendly_configured: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        agent="Danny (Strands)",
        calendly_configured=bool(os.getenv("CALENDLY_API_KEY")),
    )


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Send a message to Danny and get a response.

    The Strands agent keeps conversation history per session so it
    understands context (e.g. the user picked a time slot that was
    offered earlier).  The agent will autonomously invoke the right
    tools — get_available_appointments, book_appointment, etc.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    session_id, agent = _get_or_create_session(req.session_id)

    try:
        logger.info("[%s] User: %s", session_id, req.message[:120])
        result = agent(req.message)

        # Extract text from the agent result
        response_text = str(result)

        # Detect transfer flag
        transfer = "[TRANSFER_REQUESTED]" in response_text
        if transfer:
            response_text = response_text.split("[TRANSFER_REQUESTED]")[0].strip()
            if not response_text:
                response_text = (
                    "Let me transfer you to a staff member who can help with that."
                )

        # Clean markdown artifacts the agent may add
        response_text = response_text.strip()

        logger.info("[%s] Danny: %s", session_id, response_text[:120])

        return ChatResponse(
            reply=response_text,
            session_id=session_id,
            transfer_requested=transfer,
        )

    except Exception as e:
        logger.error("[%s] Agent error: %s", session_id, str(e), exc_info=True)
        # Only escalate to human on actual errors
        return ChatResponse(
            reply=(
                "I'm sorry, I ran into a technical issue while processing your request. "
                "Let me connect you with our staff who can help right away."
            ),
            session_id=session_id,
            transfer_requested=True,
        )


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    """End a conversation session."""
    if session_id in _sessions:
        del _sessions[session_id]
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


# ---------------------------------------------------------------------------
# TTS endpoint — converts Danny's text replies into spoken audio
# Uses Amazon Polly (neural) for natural-sounding speech.
# Falls back to a simple 400 if Polly is not available.
# ---------------------------------------------------------------------------
class TTSRequest(BaseModel):
    text: str
    voice_id: str = "Joanna"  # Neural-capable female voice


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting so Polly reads clean text."""
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # bold
    text = re.sub(r"\*(.*?)\*", r"\1", text)  # italic
    text = re.sub(r"[#]+\s?", "", text)  # headings
    text = re.sub(r"[•\-]\s?", "", text)  # bullets
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)  # images
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)  # links
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)  # code
    text = re.sub(r"[✅⚠️📅📍🦷🚨💰🛡️❓🕐📋🏥]", "", text)  # emojis
    text = re.sub(r"\n{2,}", ". ", text)  # double newlines → pause
    text = re.sub(r"\n", " ", text)  # single newlines
    text = re.sub(r"\s{2,}", " ", text)  # collapse whitespace
    return text.strip()


@app.post("/tts")
def text_to_speech(req: TTSRequest):
    """Convert text to speech audio (MP3) using Amazon Polly."""
    import io

    clean_text = _strip_markdown(req.text)
    if not clean_text:
        raise HTTPException(status_code=400, detail="No text to synthesise")

    try:
        import boto3

        polly = boto3.client(
            "polly",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

        # Truncate to 3000 chars — Polly limit is 3000 for neural
        if len(clean_text) > 3000:
            clean_text = clean_text[:2997] + "..."

        response = polly.synthesize_speech(
            Text=clean_text,
            OutputFormat="mp3",
            VoiceId=req.voice_id,
            Engine="neural",
            LanguageCode="en-US",
        )

        audio_stream = response["AudioStream"].read()
        return StreamingResponse(
            io.BytesIO(audio_stream),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=danny.mp3"},
        )

    except ImportError:
        raise HTTPException(status_code=501, detail="boto3 not installed — TTS unavailable")
    except Exception as e:
        logger.error("Polly TTS error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")


# ---------------------------------------------------------------------------
# Run with:  python api_server.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", "8000"))
    logger.info("Starting Danny AI API on port %d", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
