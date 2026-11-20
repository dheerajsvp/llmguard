"""The hash chain. Pure functions: no database, easy to test.

Each record stores the hash of the record before it:

    hash = sha256(prev_hash + canonical_json(seq, time, event))

Change any old record and its hash no longer matches; fix that hash and the *next*
record's `prev_hash` no longer matches, and so on to the end. So an edit is
detectable by re-walking the chain.

What this does NOT give you: if someone rewrites the *whole* chain from the edited
point onwards, or deletes the newest records, the chain still looks consistent.
Defence: copy `head()` (latest seq + hash) somewhere they can't reach.
"""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from llmguard.audit.events import AuditEvent

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class StoredRecord:
    seq: int
    created_at: datetime
    event: AuditEvent
    prev_hash: str
    hash: str


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    checked: int
    first_bad_seq: int | None = None
    reason: str = ""


def prompt_fingerprint(redacted_prompt: str) -> str:
    return hashlib.sha256(redacted_prompt.encode("utf-8")).hexdigest()


def _canonical(seq: int, created_at: datetime, event: AuditEvent) -> str:
    # Sorted keys + fixed separators => the same data always gives the same bytes.
    payload = {
        "seq": seq,
        "created_at": created_at.astimezone(UTC).isoformat(timespec="microseconds"),
        "request_id": event.request_id,
        "blocked": event.blocked,
        "rule_ids": list(event.rule_ids),
        "redactions": event.redactions,
        "prompt_sha256": event.prompt_sha256,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_hash(prev_hash: str, seq: int, created_at: datetime, event: AuditEvent) -> str:
    return hashlib.sha256((prev_hash + _canonical(seq, created_at, event)).encode()).hexdigest()


def link(prev: StoredRecord | None, event: AuditEvent, created_at: datetime) -> StoredRecord:
    """Build the next record in the chain after `prev` (None = start a new chain)."""
    seq = 1 if prev is None else prev.seq + 1
    prev_hash = GENESIS_HASH if prev is None else prev.hash
    return StoredRecord(
        seq, created_at, event, prev_hash, compute_hash(prev_hash, seq, created_at, event)
    )


def verify_records(records: Iterable[StoredRecord]) -> VerifyResult:
    """Walk records in seq order; report the first one that does not fit the chain."""
    expected_seq = 1
    expected_prev = GENESIS_HASH
    checked = 0
    for r in records:
        if r.seq != expected_seq:
            return VerifyResult(
                False, checked, r.seq, f"expected seq {expected_seq}, found {r.seq} (gap)"
            )
        if r.prev_hash != expected_prev:
            return VerifyResult(False, checked, r.seq, "prev_hash does not match previous record")
        if r.hash != compute_hash(r.prev_hash, r.seq, r.created_at, r.event):
            return VerifyResult(False, checked, r.seq, "record contents do not match its hash")
        expected_seq, expected_prev, checked = r.seq + 1, r.hash, checked + 1
    return VerifyResult(True, checked)
