"""
Configuration management for Danny AI.
Handles environment variables and settings.
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class ClaudeConfig:
    """Claude API configuration."""
    api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 1024
    temperature: float = 0.7


@dataclass
class AWSConfig:
    """AWS configuration for future Bedrock integration."""
    region: str = field(default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"))
    use_bedrock: bool = field(default_factory=lambda: os.getenv("USE_BEDROCK", "false").lower() == "true")
    access_key_id: Optional[str] = field(default_factory=lambda: os.getenv("AWS_ACCESS_KEY_ID"))
    secret_access_key: Optional[str] = field(default_factory=lambda: os.getenv("AWS_SECRET_ACCESS_KEY"))


@dataclass
class CalendlyConfig:
    """Calendly API configuration."""
    api_key: str = field(default_factory=lambda: os.getenv("CALENDLY_API_KEY", ""))
    base_url: str = "https://api.calendly.com"
    user_uri: Optional[str] = field(default_factory=lambda: os.getenv("CALENDLY_USER_URI"))


@dataclass
class PracticeConfig:
    """Dental practice configuration."""
    name: str = field(default_factory=lambda: os.getenv("PRACTICE_NAME", "Dental Practice"))
    phone: str = field(default_factory=lambda: os.getenv("PRACTICE_PHONE", ""))
    default_language: str = field(default_factory=lambda: os.getenv("DEFAULT_LANGUAGE", "en"))


@dataclass
class ComplianceConfig:
    """Compliance and logging configuration."""
    require_recording_consent: bool = field(
        default_factory=lambda: os.getenv("REQUIRE_RECORDING_CONSENT", "true").lower() == "true"
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


@dataclass
class DannyConfig:
    """Main configuration container for Danny AI."""
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    aws: AWSConfig = field(default_factory=AWSConfig)
    calendly: CalendlyConfig = field(default_factory=CalendlyConfig)
    practice: PracticeConfig = field(default_factory=PracticeConfig)
    compliance: ComplianceConfig = field(default_factory=ComplianceConfig)

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.claude.api_key and not self.aws.use_bedrock:
            errors.append("ANTHROPIC_API_KEY is required when not using Bedrock")
        
        if not self.calendly.api_key:
            errors.append("CALENDLY_API_KEY is required for scheduling")
        
        return errors

    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return len(self.validate()) == 0


# Global configuration instance
config = DannyConfig()


def get_config() -> DannyConfig:
    """Get the global configuration instance."""
    return config


def reload_config() -> DannyConfig:
    """Reload configuration from environment."""
    global config
    load_dotenv(override=True)
    config = DannyConfig()
    return config
