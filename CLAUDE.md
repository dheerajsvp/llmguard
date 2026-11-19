# llmguard

## Goal
Guardrails and audit toolkit between an app and the Gemini API. Per call: redact Indian PII (PAN, Aadhaar+Verhoeff, phone, UPI, email, card+Luhn), detect prompt injection (user input and retrieved docs), check the reply against policy and restore placeholders where allowed, write a hash-chained audit log to PostgreSQL (never raw PII), and show a React dashboard.

This is a portfolio project. The owner is an entry-level dev and must be able to explain every design choice in an interview.

## Stack
Python 3.11+, pydantic, FastAPI, SQLAlchemy 2 + Alembic, PostgreSQL, pytest, ruff, mypy. Frontend: React + TypeScript + Vite + Vitest + Recharts. Docker Compose. GitHub Actions. Gemini via a provider interface (Fake provider in tests/CI).

## Layout
- `src/llmguard/` core library: `pii/`, `injection/`, `policy/`, `providers/`, `audit/`, `api/`
- `tests/` pytest; `eval/` labeled datasets and eval scripts; `docs/` ROADMAP and DECISIONS
- `dashboard/` React app (created in M6)

## Commands
- Install: `pip install -e ".[dev]"`
- Test: `pytest`
- Lint/format: `ruff check . && ruff format .`
- Types: `mypy src`

## Conventions
- Test-first: write a failing test, then the code.
- Small commits, one logical change each.
- No raw PII in logs, audit rows, fixtures committed as real data, or error messages. Use synthetic data only.
- Type hints everywhere; keep the core pure (no I/O) where possible.
- Plan before each feature; work one milestone at a time (see docs/ROADMAP.md) and stop for review at the end of each. Do not skip ahead.
- Don't add dependencies without explaining why (record in docs/DECISIONS.md).
- Explain new concepts briefly as you introduce them; prefer simple code over clever code.
- Be honest in evals and the README about limitations.
