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
    public_wss_url: str = Field(
        default="",
        description="Public wss:// URL of this server (e.g. wss://xyz.ngrok-free.app)",
    )

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
    gnani_dry_run: bool = Field(
        default=False,
        description="When True, uses synthetic dry-run responses without calling Gnani APIs",
    )
    gnani_api_key: str = Field(default="", description="Gnani Vachana API key")
    gnani_stt_ws_url: str = Field(
        default="wss://api.vachana.ai/stt/v3/stream",
        description="Gnani STT WebSocket URL",
    )
    gnani_stt_model: str = Field(default="prisma-v3.0", description="STT model")
    gnani_stt_language_code: str = Field(default="hi-IN,en-IN", description="STT language code")
    gnani_stt_sample_rate: int = Field(default=8000, description="STT sample rate in Hz")
    gnani_stt_vad_threshold: float = Field(default=0.7, description="STT VAD threshold")
    gnani_stt_min_speech_ms: int = Field(default=200, description="STT min speech in ms")
    gnani_stt_min_silence_ms: int = Field(default=500, description="STT min silence in ms")
    vad_energy_threshold: float = Field(
        default=600.0,
        description="RMS energy threshold for local telephony VAD speech detection",
    )
    gnani_stt_format: str = Field(default="codemix", description="STT format (codemix/verbatim)")
    gnani_stt_keyterms: str = Field(
        default="geyser,tap,leak,motor,pipe,bathroom,kitchen",
        description="STT boosting keyterms",
    )

    gnani_tts_ws_url: str = Field(
        default="wss://api.vachana.ai/api/v1/tts",
        description="Gnani TTS WebSocket URL",
    )
    gnani_tts_model: str = Field(default="timbre-v2.5", description="TTS model")
    gnani_tts_voice: str = Field(default="Poorvi", description="TTS voice name")
    gnani_tts_language: str = Field(default="hi-en", description="TTS language code")
    gnani_tts_speed: float = Field(default=1.0, description="TTS speech rate multiplier")

    # ── Exotel ─────────────────────────────────────────────────────────────
    exotel_api_key: str = Field(default="", description="Exotel API key")
    exotel_api_token: str = Field(default="", description="Exotel API token")
    exotel_account_sid: str = Field(default="", description="Exotel account SID")
    exotel_sid: str = Field(default="", description="Alias for account SID")
    exotel_subdomain: str = Field(default="api.in.exotel.com", description="Exotel API subdomain")
    exophone_number: str = Field(default="", description="Virtual ExoPhone caller ID number")

    # ── Evon LLM ───────────────────────────────────────────────────────────
    evon_base_url: str = Field(
        default="http://localhost:8001/v1",
        description="Evon vLLM base URL (OpenAI-compatible)",
    )

    # ── Outbound call hours (24-hour IST) & Telephony Handoff ──────────────
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
    telephony_handoff_number: str = Field(
        default="+91 98765 43210",
        description="Phone number for human owner handoff on caller escalation",
    )

    @property
    def effective_exotel_sid(self) -> str:
        """Returns exotel_account_sid or exotel_sid."""
        return self.exotel_account_sid or self.exotel_sid


# Singleton instance used throughout the app
settings = Settings()
