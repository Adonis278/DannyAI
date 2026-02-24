"""
Voice integration module for Danny AI.
Handles the full AWS voice pipeline:
  Amazon Connect → KVS → Transcribe Streaming → Agent → Polly → Connect
"""

from .connect_handler import ConnectHandler
from .transcribe_handler import TranscribeHandler, StreamingTranscribeHandler
from .polly_handler import PollyHandler
from .kvs_consumer import KVSConsumer
from .voice_pipeline import VoicePipeline, PipelineConfig

__all__ = [
    "ConnectHandler",
    "TranscribeHandler",
    "StreamingTranscribeHandler",
    "PollyHandler",
    "KVSConsumer",
    "VoicePipeline",
    "PipelineConfig",
]
