# llmguard

A guardrails and audit toolkit that sits between an app and an LLM API (Gemini).

For every call it:
1. Redacts Indian PII (PAN, Aadhaar with Verhoeff check, phone, UPI ID, email, card with Luhn check) into placeholders like `<PAN_1>`
2. Detects prompt injection in user input and in retrieved/document text
3. Calls the model with the cleaned prompt, checks the reply against policy, and restores placeholders where allowed
4. Writes a hash-chained, tamper-evident audit log to PostgreSQL, never storing raw PII
5. Shows a React dashboard: violations over time, top rules, per-call drill-down

**Status:** planning/scaffold stage (see [docs/ROADMAP.md](docs/ROADMAP.md)).

## Quick start
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; use source .venv/bin/activate elsewhere
pip install -e ".[dev]"
pytest
```

## Docs
- [Roadmap](docs/ROADMAP.md)
- [Design decisions](docs/DECISIONS.md)

## Limitations (be upfront)
- Regex/heuristic prompt-injection detection is bypassable (paraphrasing, encodings, other languages). It reduces risk; it does not eliminate it.
- PII detection is pattern-based: it misses names, addresses and free-text identifiers, and number formats can cause false positives.
- Restoring placeholders in replies can reintroduce PII, so it is policy-gated.
- The hash chain detects edits only if the latest hash is anchored outside the database; someone with full DB control could rewrite the whole chain.
- Reply policy checks are heuristic. The proxy adds latency, and Gemini free-tier quotas apply.
- Evaluation sets are small and partly synthetic, so reported numbers will not generalize. Results will be published here with set sizes.
