"""Builds the real app from environment variables. Run with:

uvicorn llmguard.api.main:build_app --factory --host 0.0.0.0 --port 8000
"""

import logging

from fastapi import FastAPI
from sqlalchemy import create_engine

from llmguard.api.app import create_app
from llmguard.api.settings import Settings
from llmguard.audit.store import AuditLog
from llmguard.guard import Guard
from llmguard.policy.checks import Policy
from llmguard.providers.base import Provider
from llmguard.providers.fake import FakeProvider

logger = logging.getLogger("llmguard.api")


def build_app() -> FastAPI:
    settings = Settings.from_env()
    audit = AuditLog(create_engine(settings.database_url, pool_pre_ping=True))
    provider: Provider
    if settings.provider == "fake":
        logger.warning("LLMGUARD_PROVIDER=fake: replies are canned demo text, not a real model")
        provider = FakeProvider(reply="[demo provider] I received your message.")
    else:
        from llmguard.providers.gemini import GeminiProvider

        provider = GeminiProvider()  # reads GEMINI_API_KEY
    guard = Guard(provider, Policy(restore_types=settings.restore_types), audit=audit)
    return create_app(guard, audit, settings.chat_keys, settings.admin_keys)
