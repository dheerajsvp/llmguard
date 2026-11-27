"""Synthetic demo data, so the dashboard has something to show (screenshots, a first look).

    docker compose exec api python -m llmguard.demo --yes-delete-existing

Everything here is made up: random request ids, invented rule hits, and prompt
fingerprints of placeholder labels. No event went through the guard, so it is NOT a
record of real traffic. The chain is real (built with the same code the guard uses),
which is why the dashboard shows "Chain verified".

WARNING: writing demo data first DELETES every row in audit_events. It refuses to run
without --yes-delete-existing, and it only ever reads the database URL from the
LLMGUARD_DATABASE_URL environment variable.
"""

import argparse
import os
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from llmguard.audit.chain import StoredRecord, link, prompt_fingerprint
from llmguard.audit.events import AuditEvent

# (rule ids that fired together, relative weight). Blocked events pick one of these.
_RULE_SETS: tuple[tuple[tuple[str, ...], int], ...] = (
    (("INJ_IGNORE_PREVIOUS",), 9),
    (("INJ_IGNORE_PREVIOUS", "INJ_REVEAL_PROMPT"), 5),
    (("INJ_REVEAL_PROMPT",), 4),
    (("INJ_DOC_ADDRESSES_AI", "INJ_EXFILTRATION"), 3),
    (("INJ_MODE_SWITCH",), 2),
    (("PII_IN_REPLY",), 2),
    (("INJ_DELIMITER_SPOOF",), 1),
    (("SYSTEM_PROMPT_LEAK",), 1),
    (("INJ_ENCODED_PAYLOAD",), 1),
)
_REDACTIONS: tuple[dict[str, int], ...] = (
    {},
    {},
    {},
    {"PAN": 1},
    {"PHONE": 1},
    {"PHONE": 1, "EMAIL": 1},
    {"AADHAAR": 1},
    {"PAN": 1, "PHONE": 2},
)


def build_demo_records(now: datetime, days: int = 7, seed: int = 7) -> list[StoredRecord]:
    """A valid hash chain of synthetic events over the last `days` days, oldest first."""
    rng = random.Random(seed)
    rule_sets = [r for r, _ in _RULE_SETS]
    weights = [w for _, w in _RULE_SETS]
    records: list[StoredRecord] = []
    prev: StoredRecord | None = None
    for d in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=d)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = now if d == 0 else day_start + timedelta(hours=23, minutes=59)
        span = (day_end - day_start).total_seconds()
        count = rng.randint(20, 60) if d == 0 else rng.randint(35, 120)
        block_rate = 0.30 if d in (2, 3) else 0.17  # a couple of rougher days
        for i, offset in enumerate(sorted(rng.uniform(0, span) for _ in range(count))):
            blocked = rng.random() < block_rate
            event = AuditEvent(
                request_id=str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                blocked=blocked,
                rule_ids=rng.choices(rule_sets, weights)[0] if blocked else (),
                redactions=dict(rng.choice(_REDACTIONS)),
                prompt_sha256=prompt_fingerprint(f"demo-{seed}-{d}-{i}"),
            )
            prev = link(prev, event, day_start + timedelta(seconds=offset))
            records.append(prev)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fill the audit log with synthetic demo data.")
    parser.add_argument(
        "--yes-delete-existing",
        action="store_true",
        help="required: confirms that ALL existing audit rows will be deleted first",
    )
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)

    url = os.environ.get("LLMGUARD_DATABASE_URL", "").strip()
    if not url:
        print("LLMGUARD_DATABASE_URL is not set.", file=sys.stderr)
        return 2
    if not args.yes_delete_existing:
        target = urlparse(url)  # host and database name only: never print the password
        print(
            f"This DELETES every row in audit_events on host '{target.hostname}' "
            f"(database '{target.path.lstrip('/')}') and replaces it with synthetic demo data.\n"
            "Re-run with --yes-delete-existing if that is what you want.",
            file=sys.stderr,
        )
        return 2

    # Imported here so the pure builder above works without the optional `db` extra.
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from llmguard.audit.models import AuditRow

    records = build_demo_records(datetime.now(UTC), args.days, args.seed)
    engine = create_engine(url)
    with Session(engine) as session, session.begin():
        session.execute(text("TRUNCATE audit_events"))
        session.add_all(
            AuditRow(
                seq=r.seq,
                created_at=r.created_at,
                request_id=r.event.request_id,
                blocked=r.event.blocked,
                rule_ids=list(r.event.rule_ids),
                redactions=r.event.redactions,
                prompt_sha256=r.event.prompt_sha256,
                prev_hash=r.prev_hash,
                hash=r.hash,
            )
            for r in records
        )
    print(f"Wrote {len(records)} synthetic events over {args.days} days.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
