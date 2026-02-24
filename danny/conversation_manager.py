"""
Conversation Manager for Danny AI.
Handles session management, logging, and conversation persistence.
"""

import json
import uuid
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from .agent import ConversationContext, ConversationState


@dataclass
class ConversationLog:
    """Log entry for a completed conversation."""
    session_id: str
    start_time: str
    end_time: str
    message_count: int
    final_state: str
    consent_given: bool
    patient_name: Optional[str]
    intent: Optional[str]
    messages: list[dict]
    metadata: dict


class ConversationManager:
    """
    Manages conversation sessions and logging.
    In production, this would use DynamoDB/S3.
    For MVP, we use local file storage.
    """

    def __init__(self, log_dir: str = "data/conversations"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.active_sessions: dict[str, datetime] = {}

    def create_session(self) -> str:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        self.active_sessions[session_id] = datetime.utcnow()
        return session_id

    def log_conversation(self, context: ConversationContext) -> str:
        """
        Log a completed conversation to storage.
        Returns the log file path.
        """
        start_time = self.active_sessions.get(context.session_id, datetime.utcnow())
        end_time = datetime.utcnow()
        
        log = ConversationLog(
            session_id=context.session_id,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            message_count=len(context.messages),
            final_state=context.state.value,
            consent_given=context.consent_given,
            patient_name=context.patient_name,
            intent=context.intent,
            messages=[{"role": m.role, "content": m.content} for m in context.messages],
            metadata=context.metadata
        )
        
        # Save to file
        filename = f"{context.session_id}_{end_time.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.log_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(asdict(log), f, indent=2)
        
        # Clean up active session
        if context.session_id in self.active_sessions:
            del self.active_sessions[context.session_id]
        
        return str(filepath)

    def get_session_duration(self, session_id: str) -> Optional[float]:
        """Get the duration of an active session in seconds."""
        if session_id in self.active_sessions:
            start_time = self.active_sessions[session_id]
            return (datetime.utcnow() - start_time).total_seconds()
        return None

    def list_recent_conversations(self, limit: int = 10) -> list[dict]:
        """List recent conversation logs."""
        logs = []
        files = sorted(self.log_dir.glob("*.json"), reverse=True)[:limit]
        
        for filepath in files:
            try:
                with open(filepath, 'r') as f:
                    log_data = json.load(f)
                    logs.append({
                        "session_id": log_data["session_id"],
                        "start_time": log_data["start_time"],
                        "message_count": log_data["message_count"],
                        "intent": log_data.get("intent", "unknown")
                    })
            except Exception:
                continue
        
        return logs

    def get_conversation_log(self, session_id: str) -> Optional[dict]:
        """Retrieve a specific conversation log."""
        for filepath in self.log_dir.glob(f"{session_id}*.json"):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except Exception:
                continue
        return None


# Singleton instance
_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager() -> ConversationManager:
    """Get the singleton conversation manager instance."""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
