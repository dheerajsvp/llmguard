# llmguard

A guardrails and audit toolkit that sits between an app and an LLM API (Gemini).

For every call it:
1. Redacts Indian PII (PAN, Aadhaar with Verhoeff check, phone, UPI ID, email, card with Luhn check) into placeholders like `<PAN_1>`
2. Detects prompt injection in user input and in retrieved/document text
3. Calls the model with the cleaned prompt, checks the reply against policy, and restores placeholders where allowed
4. Writes a hash-chained, tamper-evident audit log to PostgreSQL, never storing raw PII
5. Shows a React dashboard: violations over time, top rules, per-call drill-down

**Status:** M0 to M6 done (core library, audit log, HTTP API, dashboard). Polish and write-up (M7) is next. See [docs/ROADMAP.md](docs/ROADMAP.md).

## Quick start
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; use source .venv/bin/activate elsewhere
pip install -e ".[dev,db,api]"
pytest
```

## Run the API (Docker Compose)
```bash
cp .env.example .env        # then fill in every blank (see comments in the file)
docker compose up --build   # API on http://127.0.0.1:8000 (Postgres is not exposed)

curl -X POST http://127.0.0.1:8000/v1/chat \
  -H "X-API-Key: $CHAT_KEY" -H "content-type: application/json" \
  -d '{"prompt": "My PAN is ABCPE1234F"}'
```
`LLMGUARD_PROVIDER=fake` (default) gives canned replies; set `gemini` and `GEMINI_API_KEY` for the real model.

| Endpoint | Key | Purpose |
|---|---|---|
| `POST /v1/chat` | chat | guarded model call |
| `GET /api/events`, `/api/events/{request_id}` | admin | audit log, filters, drill-down |
| `GET /api/stats?days=7` | admin | violations per day, top rules |
| `GET /api/chain` | admin | verify the hash chain, return head hash |
| `GET /healthz` | none | liveness |

## Dashboard
`docker compose up --build` also serves the dashboard at http://127.0.0.1:8088 (change with `DASHBOARD_PORT`). Paste an **admin** key on the first screen. It is kept for the browser tab only.

- **Overview:** calls, blocked, block rate, audit-chain integrity; calls per day (blocked highlighted); top triggered rules. Every chart has a "Show as table" view.
- **Events:** filter by status and rule, page through the log, open any call to see its rule ids, redaction counts and hashes. The prompt and reply are never stored, so they are never shown.

For development: `cd dashboard && npm ci && npm run dev` (needs the API on port 8000; Vite forwards `/api`). `npm test`, `npm run typecheck`, `npm run build`.

## Tests
`pytest` runs everything that needs no database. For the Postgres tests, see the DB test command in [CLAUDE.md](CLAUDE.md).

## Docs
- [Roadmap](docs/ROADMAP.md)
- [Design decisions](docs/DECISIONS.md)

## Limitations (be upfront)
- Regex/heuristic prompt-injection detection is bypassable (paraphrasing, encodings, other languages). It reduces risk; it does not eliminate it.
- PII detection is pattern-based: it misses names, addresses and free-text identifiers, and number formats can cause false positives.
- Restoring placeholders in replies can reintroduce PII, so it is policy-gated.
- The hash chain detects edits only if the latest hash is anchored outside the database; someone with full DB control could rewrite the whole chain.
- Reply policy checks are heuristic. The proxy adds latency, and Gemini free-tier quotas apply.
- The dashboard has no user accounts: anyone holding an admin key sees everything, and the Events view cannot yet filter by date. The JS bundle is about 650 kB (mostly the chart library).
- No rate limiting or per-key quotas yet; API keys are static and there is no key rotation.
- Evaluation sets are small and partly synthetic, so reported numbers will not generalize. Results will be published here with set sizes.
