"""Read-side types for the audit log (used by the API and dashboard)."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol

from llmguard.audit.chain import StoredRecord, VerifyResult


@dataclass(frozen=True)
class DayCount:
    day: date
    total: int
    blocked: int


@dataclass(frozen=True)
class RuleCount:
    rule_id: str
    count: int


@dataclass(frozen=True)
class WindowStats:
    total: int
    blocked: int
    by_day: list[DayCount] = field(default_factory=list)  # only days that had events
    top_rules: list[RuleCount] = field(default_factory=list)


class AuditReader(Protocol):
    def list_events(
        self, limit: int, offset: int, blocked: bool | None, rule_id: str | None
    ) -> tuple[list[StoredRecord], int]: ...

    def get_event(self, request_id: str) -> StoredRecord | None: ...

    def stats(self, since: datetime) -> WindowStats: ...

    def verify_chain(self) -> VerifyResult: ...

    def head(self) -> tuple[int, str] | None: ...
