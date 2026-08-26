"""
Configuration Management for Personal AI Intelligence Agent.
Loads settings from environment variables with strong typing, sensible defaults, and validation.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Optional


def _get_env(key: str, default: Optional[str] = None, required: bool = False) -> str:
    """Retrieve an environment variable or raise/fallback as configured."""
    val = os.environ.get(key, default)
    if required and (val is None or val.strip() == ""):
        raise ValueError(f"Required environment variable '{key}' is missing or empty.")
    return val if val is not None else ""


def _get_env_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _get_env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class SupabaseSettings:
    """Supabase connection and credentials configuration."""
    url: str = field(default_factory=lambda: _get_env("SUPABASE_URL", "https://localhost.supabase.co"))
    service_role_key: str = field(default_factory=lambda: _get_env("SUPABASE_SERVICE_ROLE_KEY", ""))
    anon_key: str = field(default_factory=lambda: _get_env("SUPABASE_ANON_KEY", ""))

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.service_role_key and "localhost" not in self.url)


@dataclass(frozen=True)
class GeminiSettings:
    """Google Gemini AI API configuration."""
    api_key: str = field(default_factory=lambda: _get_env("GEMINI_API_KEY", ""))
    model_name: str = field(default_factory=lambda: _get_env("GEMINI_MODEL", "gemini-2.5-flash"))
    prompt_version: str = "v1.0.0"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key != "MY_GEMINI_API_KEY")


@dataclass(frozen=True)
class DiscordSettings:
    """Discord notifications and bot configuration."""
    webhook_url: str = field(default_factory=lambda: _get_env("DISCORD_WEBHOOK_URL", ""))
    bot_token: str = field(default_factory=lambda: _get_env("DISCORD_BOT_TOKEN", ""))
    channel_id: str = field(default_factory=lambda: _get_env("DISCORD_CHANNEL_ID", ""))

    @property
    def is_configured(self) -> bool:
        return bool(self.webhook_url or self.bot_token)


@dataclass(frozen=True)
class CollectorSettings:
    """Ingestion limits, timeouts, and user agent parameters."""
    check_interval_minutes: int = field(default_factory=lambda: _get_env_int("COLLECTION_INTERVAL_MINUTES", 60))
    max_articles_per_run: int = field(default_factory=lambda: _get_env_int("MAX_ARTICLES_PER_RUN", 50))
    max_ai_calls_per_run: int = field(default_factory=lambda: _get_env_int("MAX_AI_CALLS_PER_RUN", 30))
    request_timeout_seconds: int = field(default_factory=lambda: _get_env_int("HTTP_REQUEST_TIMEOUT_SECONDS", 15))
    user_agent: str = field(default_factory=lambda: _get_env(
        "USER_AGENT",
        "Mozilla/5.0 (compatible; PersonalIntelligenceAgent/1.0; +https://github.com/user/ai-intelligence-agent)"
    ))


@dataclass(frozen=True)
class UserPreferenceSettings:
    """User context targeting 2025 engineering scheme and interest levels."""
    scheme: str = field(default_factory=lambda: _get_env("USER_SCHEME", "2025"))
    branch: str = field(default_factory=lambda: _get_env("USER_BRANCH", "CSE"))
    semester: str = field(default_factory=lambda: _get_env("USER_SEMESTER", "1"))
    ai_interest: int = field(default_factory=lambda: _get_env_int("USER_AI_INTEREST", 4))
    dev_interest: int = field(default_factory=lambda: _get_env_int("USER_DEV_INTEREST", 4))
    cyber_interest: int = field(default_factory=lambda: _get_env_int("USER_CYBER_INTEREST", 5))


@dataclass(frozen=True)
class Settings:
    """Root Application Configuration."""
    app_env: str = field(default_factory=lambda: _get_env("APP_ENV", "development"))
    log_level: str = field(default_factory=lambda: _get_env("LOG_LEVEL", "INFO"))
    supabase: SupabaseSettings = field(default_factory=SupabaseSettings)
    gemini: GeminiSettings = field(default_factory=GeminiSettings)
    discord: DiscordSettings = field(default_factory=DiscordSettings)
    collector: CollectorSettings = field(default_factory=CollectorSettings)
    preferences: UserPreferenceSettings = field(default_factory=UserPreferenceSettings)

    def validate_for_production(self) -> list[str]:
        """Verify presence of production-critical secrets and configs."""
        errors: list[str] = []
        if self.app_env == "production":
            if not self.supabase.is_configured:
                errors.append("Supabase URL and Service Role Key must be set in production.")
            if not self.gemini.is_configured:
                errors.append("GEMINI_API_KEY must be set in production.")
            if not self.discord.is_configured:
                errors.append("DISCORD_WEBHOOK_URL or DISCORD_BOT_TOKEN must be set in production.")
        return errors


_global_settings: Optional[Settings] = None


def get_settings(reload: bool = False) -> Settings:
    """Get singleton Settings instance."""
    global _global_settings
    if _global_settings is None or reload:
        _global_settings = Settings()
    return _global_settings
