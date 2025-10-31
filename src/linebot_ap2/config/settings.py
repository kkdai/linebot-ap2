"""Configuration settings for LINE Bot AP2 application."""

import os
import sys
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # LINE Bot Configuration
    line_channel_secret: str = Field(alias="ChannelSecret")
    line_channel_access_token: str = Field(alias="ChannelAccessToken")
    
    # Google AI Configuration
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    google_genai_use_vertexai: bool = Field(default=False, alias="GOOGLE_GENAI_USE_VERTEXAI")
    google_cloud_project: Optional[str] = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    google_cloud_location: Optional[str] = Field(default=None, alias="GOOGLE_CLOUD_LOCATION")
    
    # Application Configuration
    app_name: str = "linebot_ap2"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8080
    
    # Agent Configuration
    default_model: str = "gemini-2.5-flash"
    session_timeout_minutes: int = 30
    max_otp_attempts: int = 3
    otp_expiry_minutes: int = 5
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }
    
    @field_validator("google_genai_use_vertexai", mode="before")
    @classmethod
    def parse_use_vertexai(cls, v):
        """Parse GOOGLE_GENAI_USE_VERTEXAI environment variable."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return bool(v)
    
    @field_validator("google_cloud_project")
    @classmethod
    def validate_vertex_ai_config(cls, v, info):
        """Validate Vertex AI configuration when enabled."""
        if info.data.get("google_genai_use_vertexai") and not v:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT is required when GOOGLE_GENAI_USE_VERTEXAI is True"
            )
        return v
    
    @field_validator("google_cloud_location")
    @classmethod
    def validate_vertex_ai_location(cls, v, info):
        """Validate Vertex AI location when enabled."""
        if info.data.get("google_genai_use_vertexai") and not v:
            raise ValueError(
                "GOOGLE_CLOUD_LOCATION is required when GOOGLE_GENAI_USE_VERTEXAI is True"
            )
        return v
    
    @field_validator("google_api_key")
    @classmethod
    def validate_google_api_key(cls, v, info):
        """Validate Google API key when not using Vertex AI."""
        if not info.data.get("google_genai_use_vertexai") and not v:
            raise ValueError(
                "GOOGLE_API_KEY is required when GOOGLE_GENAI_USE_VERTEXAI is False"
            )
        return v


def get_settings() -> Settings:
    """Get application settings instance."""
    try:
        return Settings()
    except Exception as e:
        print(f"Configuration error: {e}")
        sys.exit(1)


def validate_environment():
    """Validate required environment variables."""
    settings = get_settings()
    
    # Validate LINE Bot configuration
    if not settings.line_channel_secret:
        print("Error: ChannelSecret environment variable is required")
        sys.exit(1)
    
    if not settings.line_channel_access_token:
        print("Error: ChannelAccessToken environment variable is required")
        sys.exit(1)
    
    # Validate Google AI configuration
    if settings.google_genai_use_vertexai:
        if not settings.google_cloud_project:
            print("Error: GOOGLE_CLOUD_PROJECT is required when using Vertex AI")
            sys.exit(1)
        if not settings.google_cloud_location:
            print("Error: GOOGLE_CLOUD_LOCATION is required when using Vertex AI")
            sys.exit(1)
    else:
        if not settings.google_api_key:
            print("Error: GOOGLE_API_KEY is required when not using Vertex AI")
            sys.exit(1)
    
    print("✓ Environment configuration validated successfully")
    return settings