# Roadmap

Each milestone: test-first, small commits, stop for review at the end.

- [x] **M0 Scaffold**: pyproject, src/tests layout, ruff + mypy + pytest, CI skeleton
- [x] **M1 PII detection/redaction**: PAN, Aadhaar (Verhoeff), phone, UPI, email, card (Luhn); `<TYPE_n>` placeholders; same value maps to same placeholder; overlap resolution
- [x] **M2 Library wrapper**: `Guard.run()`, provider interface, Gemini + Fake providers, policy-gated placeholder restore, reply policy checks
- [x] **M3 Prompt-injection detection**: rule set, user input and retrieved docs scanned separately, labeled eval set + eval script and report
- [x] **M4 Audit log**: Postgres models, Alembic, hash chain, `verify_chain`, tamper test, no-raw-PII test
- [ ] **M5 FastAPI proxy**: `/v1/chat`, read API for events/stats, API key auth, Docker Compose (api + postgres)
- [ ] **M6 React dashboard**: violations over time, top rules, per-call drill-down, chain-status badge
- [ ] **M7 Polish**: README with eval numbers, limitations, diagram, demo GIF, CI green, threat model note

## Evaluation (cross-cutting)
Labeled sets in `eval/` with a dev/test split fixed before tuning. Report precision, recall, F1, false positives, set sizes and known bypasses. See the approved plan for details.
