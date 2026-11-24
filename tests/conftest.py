"""Shared fixtures. Database fixtures only work when LLMGUARD_TEST_DATABASE_URL is set."""

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

DB_URL = os.environ.get("LLMGUARD_TEST_DATABASE_URL")
needs_db = pytest.mark.skipif(not DB_URL, reason="LLMGUARD_TEST_DATABASE_URL not set")
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Any]:
    if not DB_URL:
        pytest.skip("LLMGUARD_TEST_DATABASE_URL not set")
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", DB_URL.replace("%", "%%"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")  # exercises the real migration, not create_all()
    engine = create_engine(DB_URL)
    yield engine
    engine.dispose()


@pytest.fixture
def audit_log(db_engine: Any) -> Any:
    from sqlalchemy import text

    from llmguard.audit.store import AuditLog

    with db_engine.begin() as conn:
        conn.execute(text("TRUNCATE audit_events"))
    return AuditLog(db_engine)
