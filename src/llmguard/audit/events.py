"""What gets audited. Deliberately contains no raw prompt, reply or PII value."""

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class AuditEvent:
    request_id: str
    blocked: bool
    # Which rules fired (e.g. "INJ_IGNORE_PREVIOUS"), in order, without duplicates.
    rule_ids: tuple[str, ...]
    # PII type -> number of distinct values redacted. Counts only.
    redactions: dict[str, int] = field(default_factory=dict)
    # SHA-256 of the *redacted* prompt. Lets you match a call to a prompt you hold
    # without the log ever storing the prompt itself.
    prompt_sha256: str = ""


class AuditSink(Protocol):
    """Anything Guard can write events to (Postgres log, in-memory list in tests)."""

    def append(self, event: AuditEvent) -> object: ...
