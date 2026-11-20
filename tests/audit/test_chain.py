from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from llmguard.audit.chain import (
    GENESIS_HASH,
    StoredRecord,
    compute_hash,
    link,
    prompt_fingerprint,
    verify_records,
)
from llmguard.audit.events import AuditEvent

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def event(n: int = 0, **kw: object) -> AuditEvent:
    base = {
        "request_id": f"req-{n}",
        "blocked": False,
        "rule_ids": ("INJ_IGNORE_PREVIOUS",),
        "redactions": {"PAN": 1},
        "prompt_sha256": prompt_fingerprint(f"prompt {n}"),
    }
    base.update(kw)
    return AuditEvent(**base)  # type: ignore[arg-type]


def build_chain(n: int) -> list[StoredRecord]:
    records: list[StoredRecord] = []
    prev: StoredRecord | None = None
    for i in range(1, n + 1):
        prev = link(prev, event(i), T0 + timedelta(seconds=i))
        records.append(prev)
    return records


def test_first_record_links_to_genesis() -> None:
    r = link(None, event(), T0)
    assert r.seq == 1 and r.prev_hash == GENESIS_HASH


def test_next_record_links_to_previous_hash() -> None:
    a = link(None, event(1), T0)
    b = link(a, event(2), T0)
    assert b.seq == 2 and b.prev_hash == a.hash


def test_hash_is_deterministic_and_hex_sha256() -> None:
    h1 = compute_hash(GENESIS_HASH, 1, T0, event())
    h2 = compute_hash(GENESIS_HASH, 1, T0, event())
    assert h1 == h2 and len(h1) == 64 and int(h1, 16) >= 0


def test_hash_ignores_redaction_dict_order() -> None:
    e1 = event(redactions={"PAN": 1, "PHONE": 2})
    e2 = event(redactions={"PHONE": 2, "PAN": 1})
    assert compute_hash(GENESIS_HASH, 1, T0, e1) == compute_hash(GENESIS_HASH, 1, T0, e2)


@pytest.mark.parametrize(
    "changed",
    [
        {"blocked": True},
        {"rule_ids": ()},
        {"redactions": {"PAN": 2}},
        {"prompt_sha256": "0" * 64},
        {"request_id": "other"},
    ],
)
def test_hash_changes_when_any_event_field_changes(changed: dict[str, object]) -> None:
    base = compute_hash(GENESIS_HASH, 1, T0, event())
    assert compute_hash(GENESIS_HASH, 1, T0, replace(event(), **changed)) != base


def test_hash_changes_with_seq_time_and_prev() -> None:
    base = compute_hash(GENESIS_HASH, 1, T0, event())
    assert compute_hash(GENESIS_HASH, 2, T0, event()) != base
    assert compute_hash(GENESIS_HASH, 1, T0 + timedelta(seconds=1), event()) != base
    assert compute_hash("1" * 64, 1, T0, event()) != base


def test_prompt_fingerprint_is_sha256_of_text() -> None:
    fp = prompt_fingerprint("hello <PAN_1>")
    assert len(fp) == 64 and "hello" not in fp


def test_empty_chain_is_valid() -> None:
    r = verify_records([])
    assert r.ok and r.checked == 0


def test_untouched_chain_verifies() -> None:
    r = verify_records(build_chain(5))
    assert r.ok and r.checked == 5 and r.first_bad_seq is None


def test_edited_record_is_detected_at_that_record() -> None:
    chain = build_chain(5)
    chain[2] = replace(chain[2], event=replace(chain[2].event, blocked=True))
    r = verify_records(chain)
    assert not r.ok and r.first_bad_seq == 3


def test_edit_plus_recomputed_hash_breaks_the_next_link() -> None:
    # A smarter attacker fixes the edited row's own hash. The *next* row still
    # points at the old hash, so the chain breaks one step later.
    chain = build_chain(5)
    forged_event = replace(chain[2].event, blocked=True)
    forged = replace(
        chain[2],
        event=forged_event,
        hash=compute_hash(chain[2].prev_hash, 3, chain[2].created_at, forged_event),
    )
    chain[2] = forged
    r = verify_records(chain)
    assert not r.ok and r.first_bad_seq == 4


def test_deleted_middle_record_is_detected() -> None:
    chain = build_chain(5)
    del chain[1]
    r = verify_records(chain)
    assert not r.ok and r.first_bad_seq == 3


def test_deleted_first_record_is_detected() -> None:
    r = verify_records(build_chain(3)[1:])
    assert not r.ok and r.first_bad_seq == 2
