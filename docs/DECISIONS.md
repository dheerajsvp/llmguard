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

## D9. google-genai as an optional extra
Added in M2 as `pip install -e ".[gemini]"` (the official Gemini SDK). It is optional and imported lazily, so the core library, tests and CI never need it or an API key.

## D10. Restoring PII is opt-in
`Policy.restore_types` defaults to empty. Restoring placeholders re-exposes PII in the reply, so each type must be allowed explicitly. Restore never happens when a reply is blocked.

## D11. Reply checks run before restore
Checks inspect the reply with placeholders still in place. Raw PII there means the model produced it itself, which is a violation. System-prompt leak uses a 6-word verbatim-overlap window: simple to explain, but easy to evade with paraphrase.

## D12. Injection rules run on normalized text, per source
Text is NFKC-normalized, lower-cased, stripped of zero-width characters and whitespace-collapsed before matching, which defeats cheap obfuscation. User text and retrieved documents are scanned separately: some rules (addressing "the AI", exfiltration to a URL/email) are document-only because they are normal in a user message but a strong indirect-injection signal inside retrieved content.

## D13. Injection blocks before the model is called
With `block_on_violation=True`, an injection hit returns a refusal without calling the provider (no cost, no exposure). Findings carry only a rule id and a source, never the matched text.

## D14. Documents are redacted and fenced
`Guard.run(documents=[...])` redacts PII in documents too and appends them under a header marking them as untrusted data. The header is a weak mitigation, not a guarantee.

## D15. Honest evals over impressive ones
Eval sets include hard negatives and known-bypass attacks, and the README of `eval/` states the test split is not blind. Numbers are reported with n.
