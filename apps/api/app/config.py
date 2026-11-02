"""
Pakka API configuration via pydantic-settings.

All settings are loaded from environment variables (and .env for local dev).
No secrets are hard-coded here; see .env.example for the full list.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Pakka API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────
    app_env: str = Field(default="development", description="Runtime environment")
    secret_key: str = Field(default="change_me", description="Secret key for signing")

    # ── Database ───────────────────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite:///./pakka.db",
        description="SQLModel/SQLAlchemy connection string",
    )

    # ── CORS ───────────────────────────────────────────────────────────────
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Allowed CORS origins",
    )

    # ── Gnani Vachana ──────────────────────────────────────────────────────
    gnani_api_key: str = Field(default="", description="Gnani Vachana API key")
    gnani_stt_ws_url: str = Field(
        default="wss://api.vachana.ai/stt/v3/stream",
        description="Gnani STT WebSocket URL",
    )
    gnani_tts_ws_url: str = Field(
        default="wss://api.vachana.ai/api/v1/tts",
        description="Gnani TTS WebSocket URL",
    )

    # ── Exotel ─────────────────────────────────────────────────────────────
    exotel_api_key: str = Field(default="", description="Exotel API key")
    exotel_api_token: str = Field(default="", description="Exotel API token")
    exotel_sid: str = Field(default="", description="Exotel account SID")
    exotel_subdomain: str = Field(default="", description="Exotel API subdomain")

    # ── Evon LLM ───────────────────────────────────────────────────────────
    evon_base_url: str = Field(
        default="http://localhost:8001/v1",
        description="Evon vLLM base URL (OpenAI-compatible)",
    )

    # ── Outbound call hours (24-hour IST) ──────────────────────────────────
    outbound_hours_start: int = Field(
        default=9,
        ge=0,
        le=23,
        description="Earliest hour to place outbound calls (IST)",
    )
    outbound_hours_end: int = Field(
        default=20,
        ge=0,
        le=23,
        description="Latest hour to place outbound calls (IST)",
    )


# Singleton instance used throughout the app
settings = Settings()

