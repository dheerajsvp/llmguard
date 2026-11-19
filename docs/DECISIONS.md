# Design decisions

## D1. Library core + thin FastAPI proxy
Core logic is a pure Python package so it is unit-testable without network or DB and reusable as a library. The proxy and dashboard API only wrap it.

## D2. FastAPI only (no Django/DRF)
Lightweight and a good fit for a proxy; avoids running two frameworks.

## D3. Provider interface; Gemini locally, Fake in CI
Tests are free, fast and deterministic. A real key is only needed for demos.

## D4. Docker Compose only for deployment
One command to run Postgres + API + dashboard; easy for reviewers to try.

## D5. Rule/heuristic injection detection
Simple and explainable. Evaluated honestly on a labeled set; bypasses are documented, not hidden.

## D6. Placeholders live in memory only
The placeholder-to-value map exists per request and is never persisted. Audit rows store rule IDs, entity types, counts and a hash of the redacted prompt.

## D7. Hash-chained audit log
`hash = sha256(prev_hash + canonical_json(row))`; appends serialized with a Postgres advisory lock. Tamper-evident only if the head hash is anchored externally (documented limitation).

## D8. Minimal dependencies at the start
Only pydantic and dev tools in M0. Each later dependency (FastAPI, SQLAlchemy, Alembic, google-genai, etc.) is added in its milestone with a justification recorded here.
