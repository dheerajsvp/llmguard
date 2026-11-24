"""Postgres-backed audit log (needs the `db` extra)."""

from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import ColumnElement, Engine, func, select, text
from sqlalchemy.orm import Session

from llmguard.audit.chain import StoredRecord, VerifyResult, link, verify_records
from llmguard.audit.events import AuditEvent
from llmguard.audit.models import AuditRow
from llmguard.audit.reader import DayCount, RuleCount, WindowStats

# Arbitrary constant identifying "the audit chain" lock in Postgres.
_ADVISORY_LOCK_KEY = 7_243_001


def _to_record(row: AuditRow) -> StoredRecord:
    event = AuditEvent(
        request_id=row.request_id,
        blocked=row.blocked,
        rule_ids=tuple(row.rule_ids),
        redactions=dict(row.redactions),
        prompt_sha256=row.prompt_sha256,
    )
    return StoredRecord(row.seq, row.created_at, event, row.prev_hash, row.hash)


class AuditLog:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def append(self, event: AuditEvent) -> StoredRecord:
        """Add one event to the chain.

        Two requests at once could both read the same "latest" row and both extend
        it, forking the chain. The advisory lock makes appends take turns: Postgres
        releases it automatically when the transaction ends.
        """
        with Session(self.engine) as session, session.begin():
            session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _ADVISORY_LOCK_KEY})
            last = session.scalars(select(AuditRow).order_by(AuditRow.seq.desc()).limit(1)).first()
            record = link(_to_record(last) if last else None, event, datetime.now(UTC))
            session.add(
                AuditRow(
                    seq=record.seq,
                    created_at=record.created_at,
                    request_id=event.request_id,
                    blocked=event.blocked,
                    rule_ids=list(event.rule_ids),
                    redactions=event.redactions,
                    prompt_sha256=event.prompt_sha256,
                    prev_hash=record.prev_hash,
                    hash=record.hash,
                )
            )
        return record

    def _iter_records(self) -> Iterator[StoredRecord]:
        with Session(self.engine) as session:
            for row in session.scalars(select(AuditRow).order_by(AuditRow.seq)).yield_per(500):
                yield _to_record(row)

    def verify_chain(self) -> VerifyResult:
        return verify_records(self._iter_records())

    def head(self) -> tuple[int, str] | None:
        """Latest (seq, hash). Copy this somewhere outside the database to anchor the chain."""
        with Session(self.engine) as session:
            last = session.scalars(select(AuditRow).order_by(AuditRow.seq.desc()).limit(1)).first()
            return (last.seq, last.hash) if last else None

    def list_events(
        self, limit: int, offset: int, blocked: bool | None, rule_id: str | None
    ) -> tuple[list[StoredRecord], int]:
        """Newest first. Returns (page of records, total matching the filters)."""
        conds: list[ColumnElement[bool]] = []
        if blocked is not None:
            conds.append(AuditRow.blocked.is_(blocked))
        if rule_id:
            conds.append(AuditRow.rule_ids.contains([rule_id]))  # JSONB: rule_ids @> '["RULE"]'
        with Session(self.engine) as session:
            total = session.scalar(select(func.count()).select_from(AuditRow).where(*conds)) or 0
            rows = session.scalars(
                select(AuditRow)
                .where(*conds)
                .order_by(AuditRow.seq.desc())
                .limit(limit)
                .offset(offset)
            ).all()
            return [_to_record(r) for r in rows], total

    def get_event(self, request_id: str) -> StoredRecord | None:
        with Session(self.engine) as session:
            row = session.scalars(select(AuditRow).where(AuditRow.request_id == request_id)).first()
            return _to_record(row) if row else None

    def stats(self, since: datetime) -> WindowStats:
        """Counts per UTC day and the most-triggered rules, for events at/after `since`."""
        day = func.date(func.timezone("UTC", AuditRow.created_at))
        with Session(self.engine) as session:
            day_rows = session.execute(
                select(day, func.count(), func.count().filter(AuditRow.blocked))
                .where(AuditRow.created_at >= since)
                .group_by(day)
                .order_by(day)
            ).all()
            # jsonb_array_elements_text turns each rule id inside the JSON array into its own row.
            rule_rows = session.execute(
                text(
                    "SELECT r AS rule_id, count(*) AS n "
                    "FROM audit_events, jsonb_array_elements_text(rule_ids) AS r "
                    "WHERE created_at >= :since GROUP BY r ORDER BY n DESC, r LIMIT 10"
                ),
                {"since": since},
            ).all()
        by_day = [DayCount(d, int(t), int(b)) for d, t, b in day_rows]
        return WindowStats(
            total=sum(d.total for d in by_day),
            blocked=sum(d.blocked for d in by_day),
            by_day=by_day,
            top_rules=[RuleCount(r, int(n)) for r, n in rule_rows],
        )
