"""Configuration from environment variables. Refuses to start if it is unsafe."""

import os
from collections.abc import Mapping
from dataclasses import dataclass

MIN_KEY_LENGTH = 16


class SettingsError(ValueError):
    """Bad configuration. Messages name the variable, never its value."""


def _keys(env: Mapping[str, str], name: str) -> frozenset[str]:
    raw = env.get(name, "")
    keys = frozenset(k.strip() for k in raw.split(",") if k.strip())
    if not keys:
        raise SettingsError(f"{name} is required (comma-separated list of keys)")
    if any(len(k) < MIN_KEY_LENGTH for k in keys):
        raise SettingsError(f"{name}: every key must be at least {MIN_KEY_LENGTH} characters")
    return keys


@dataclass(frozen=True)
class Settings:
    database_url: str
    chat_keys: frozenset[str]  # may call POST /v1/chat
    admin_keys: frozenset[str]  # may call the read API (dashboard)
    provider: str = "gemini"  # "gemini" or "fake" (demo mode, needs no API key)
    restore_types: frozenset[str] = frozenset()

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        database_url = env.get("LLMGUARD_DATABASE_URL", "").strip()
        if not database_url:
            raise SettingsError("LLMGUARD_DATABASE_URL is required")
        chat = _keys(env, "LLMGUARD_API_KEYS")
        admin = _keys(env, "LLMGUARD_ADMIN_KEYS")
        if chat & admin:
            raise SettingsError("LLMGUARD_API_KEYS and LLMGUARD_ADMIN_KEYS must not overlap")
        provider = env.get("LLMGUARD_PROVIDER", "gemini").strip().lower()
        if provider not in {"gemini", "fake"}:
            raise SettingsError("LLMGUARD_PROVIDER must be 'gemini' or 'fake'")
        restore = frozenset(
            t.strip().upper() for t in env.get("LLMGUARD_RESTORE_TYPES", "").split(",") if t.strip()
        )
        return cls(database_url, chat, admin, provider, restore)
