from datetime import UTC, datetime, timedelta

import pytest

from llmguard.audit.chain import verify_records
from llmguard.demo import build_demo_records, main

NOW = datetime(2026, 11, 24, 15, 30, tzinfo=UTC)


def test_demo_chain_is_valid_and_spans_the_requested_days() -> None:
    records = build_demo_records(NOW, days=7, seed=7)
    assert len(records) > 100
    assert verify_records(records).ok
    days = {r.created_at.date() for r in records}
    assert len(days) == 7
    assert max(days) == NOW.date()


def test_demo_events_are_in_the_past_and_in_time_order() -> None:
    records = build_demo_records(NOW, days=7, seed=7)
    times = [r.created_at for r in records]
    assert times == sorted(times)
    assert times[-1] <= NOW
    assert times[0] >= NOW - timedelta(days=7)


def test_demo_is_deterministic_for_a_seed_and_differs_across_seeds() -> None:
    a = build_demo_records(NOW, seed=1)
    b = build_demo_records(NOW, seed=1)
    c = build_demo_records(NOW, seed=2)
    assert [r.hash for r in a] == [r.hash for r in b]
    assert [r.hash for r in a] != [r.hash for r in c]


def test_blocked_events_have_rules_and_allowed_ones_do_not() -> None:
    records = build_demo_records(NOW)
    assert any(r.event.blocked for r in records) and any(not r.event.blocked for r in records)
    for r in records:
        assert bool(r.event.rule_ids) == r.event.blocked


def test_demo_events_hold_no_prompt_text() -> None:
    for r in build_demo_records(NOW):
        assert set(r.event.redactions) <= {"PAN", "PHONE", "EMAIL", "AADHAAR", "UPI", "CARD"}
        assert len(r.event.prompt_sha256) == 64


def test_refuses_to_delete_without_the_explicit_flag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LLMGUARD_DATABASE_URL", "postgresql+psycopg://u:p@nowhere.invalid/db")
    assert main([]) == 2  # must exit before ever touching the database
    err = capsys.readouterr().err
    assert "--yes-delete-existing" in err and "p@nowhere" not in err  # never echoes the password


def test_requires_a_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLMGUARD_DATABASE_URL", raising=False)
    assert main(["--yes-delete-existing"]) == 2
