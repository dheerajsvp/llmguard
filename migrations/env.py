"""Alembic environment. URL precedence: programmatic config, then LLMGUARD_DATABASE_URL."""

import os

from alembic import context
from sqlalchemy import create_engine

from llmguard.audit.models import Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    url = config.get_main_option("sqlalchemy.url") or os.environ.get("LLMGUARD_DATABASE_URL")
    if not url:
        raise RuntimeError("Set LLMGUARD_DATABASE_URL (e.g. postgresql+psycopg://user:pw@host/db)")
    return url


def run_migrations_online() -> None:
    engine = create_engine(_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations_online()
