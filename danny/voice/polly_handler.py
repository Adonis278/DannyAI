"""
Amazon Polly handler for Danny AI.
Converts text responses to speech.
"""

import boto3
from typing import Optional
import os

from ..config import get_config


class PollyHandler:
    """Handles text-to-speech using Amazon Polly."""
    
    def __init__(self):
        self.config = get_config()
        
        # Set credentials
        os.environ["AWS_ACCESS_KEY_ID"] = self.config.aws.access_key_id or ""
        os.environ["AWS_SECRET_ACCESS_KEY"] = self.config.aws.secret_access_key or ""
        os.environ["AWS_DEFAULT_REGION"] = self.config.aws.region
        
        self.client = boto3.client(
            "polly",
            region_name=self.config.aws.region
        )
        
        # Voice configuration
        self.voice_id = "Joanna"  # Professional female voice
        self.engine = "neural"    # Neural engine for more natural speech
        self.language_code = "en-US"

    def synthesize_speech(
        self,
        text: str,
        output_format: str = "mp3",
        voice_id: Optional[str] = None
    ) -> bytes:
        """
        Convert text to speech audio.
        
        Args:
            text: The text to convert to speech
            output_format: Audio format (mp3, ogg_vorbis, pcm)
            voice_id: Optional override for voice
            
        Returns:
            Audio bytes
        """
        response = self.client.synthesize_speech(
            Text=text,
            OutputFormat=output_format,
            VoiceId=voice_id or self.voice_id,
            Engine=self.engine,
            LanguageCode=self.language_code
        )
        
        return response["AudioStream"].read()

    def synthesize_speech_ssml(
        self,
        ssml: str,
        output_format: str = "mp3"
    ) -> bytes:
        """
        Convert SSML-formatted text to speech.
        SSML allows for more control over pronunciation, pauses, etc.
        
        Args:
            ssml: SSML-formatted text
            output_format: Audio format
            
        Returns:
            Audio bytes
        """
        response = self.client.synthesize_speech(
            Text=ssml,
            TextType="ssml",
            OutputFormat=output_format,
            VoiceId=self.voice_id,
            Engine=self.engine
        )
        
        return response["AudioStream"].read()

    def get_available_voices(self, language_code: str = "en-US") -> list[dict]:
        """Get list of available voices for a language."""
        response = self.client.describe_voices(
            LanguageCode=language_code,
            Engine=self.engine
        )
        return response.get("Voices", [])

    def set_voice(self, voice_id: str):
        """Change the voice used for synthesis."""
        self.voice_id = voice_id

    def set_spanish_voice(self):
        """Switch to Spanish voice for bilingual support."""
        self.voice_id = "Lupe"  # Neural Spanish voice
        self.language_code = "es-US"

    def set_english_voice(self):
        """Switch to English voice."""
        self.voice_id = "Joanna"
        self.language_code = "en-US"


# Singleton instance
_polly_handler: Optional[PollyHandler] = None


def get_polly_handler() -> PollyHandler:
    """Get the singleton Polly handler."""
    global _polly_handler
    if _polly_handler is None:
        _polly_handler = PollyHandler()
    return _polly_handler
