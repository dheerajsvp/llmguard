"""SQLAlchemy table definition for the audit log (needs the `db` extra)."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AuditRow(Base):
    __tablename__ = "audit_events"

    # Assigned by the application inside the advisory lock (not auto-increment),
    # because the chain needs gap-free, strictly ordered numbers.
    seq: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    request_id: Mapped[str] = mapped_column(String(64), unique=True)
    blocked: Mapped[bool] = mapped_column(Boolean)
    rule_ids: Mapped[list[str]] = mapped_column(JSONB)
    redactions: Mapped[dict[str, Any]] = mapped_column(JSONB)
    prompt_sha256: Mapped[str] = mapped_column(String(64))
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)
