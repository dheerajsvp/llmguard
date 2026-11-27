# Threat model

What llmguard protects, from whom, and, just as important, what it does **not** protect.
This is a portfolio project, not a certified product. Nothing here is a compliance claim
(for example under India's DPDP Act).

## What is being protected

| Asset | Why it matters |
|---|---|
| Personal data in prompts and documents (PAN, Aadhaar, phone, UPI, email, card) | Sending it to a third-party model is a privacy and regulatory risk |
| The model's behaviour | An attacker should not be able to replace the developer's instructions |
| The system prompt | Often contains business rules or secrets |
| Integrity of the audit log | A governance log nobody can trust is worthless |
| Admin and chat API keys | They gate access to the model and to the audit data |

## Trust boundaries

```
 caller app ──(chat key)──▶ llmguard API ──▶ Gemini   (third party: sees only redacted text)
                                │
                                ▼
                            PostgreSQL        (audit log: counts, rule ids, hashes only)
                                ▲
 admin browser ──(admin key)──▶ dashboard (nginx) ──/api──▶ llmguard API
```

**Assumed trusted:** the machine running llmguard, its database, and the person who holds
the admin key. **Assumed untrusted:** end-user prompts, retrieved documents, the model's
replies, and anything reaching the API without a valid key.

## Threats and what is done about them

| # | Threat | What llmguard does | Residual risk (be upfront) |
|---|---|---|---|
| 1 | PII leaves your system inside a prompt | Redacts PAN, Aadhaar (Verhoeff), card (Luhn), phone, UPI, email into placeholders before the model call; the placeholder map lives only in memory | Names, addresses, landlines and free-text identifiers are **not** detected. Unusual formatting (for example `2345 67890124`) is missed. Checksums prove a number is well-formed, not that it is real |
| 2 | Direct prompt injection ("ignore previous instructions") | Rule-based detection on normalised text (case, invisible characters, line breaks, base64); blocks **before** the model is called | Paraphrase, non-English text and heavy obfuscation get through. Measured recall is about 0.9 on a small, non-blind set. Treat as a speed bump, not a wall |
| 3 | Indirect injection hidden in retrieved documents | Documents are scanned separately with document-only rules, redacted, and fenced as "untrusted data" | The fence is a hint to the model, not enforcement. Anything the rules don't recognise reaches the model |
| 4 | The model leaks PII or its system prompt in a reply | Reply checks run before any placeholder is restored: raw PII in the reply, 6 consecutive system-prompt words, blocked terms; blocked replies are withheld | A paraphrased system prompt is not caught. There is no toxicity or harmful-content classifier |
| 5 | Someone edits or deletes audit history | Hash chain (`hash = sha256(prev_hash + record)`); `verify_chain` and the dashboard detect an edit, a deletion or a gap | **Rewriting the whole chain from an edit onward, or deleting the newest rows, still verifies.** The fix is to copy `head()` somewhere the attacker cannot reach; that is not automated. A database admin can still alter data; the chain only makes it detectable. No DB trigger blocks UPDATE or DELETE |
| 6 | The audit log becomes a PII store | Only request id, blocked flag, rule ids, redaction *counts*, and a SHA-256 of the *redacted* prompt are stored; a test dumps the whole table and searches it for secrets | The fingerprint of a short, guessable redacted prompt could be confirmed by guessing. Metadata (timing, rule ids) can still be sensitive |
| 7 | Unauthorised use of the API | Two key roles (chat vs admin, wrong role gets 403), constant-time comparison, keys at least 16 characters, server refuses to start with missing, short or overlapping keys | Keys are static: no rotation, no per-user identity, no lockout, **no rate limiting**. Keys live in environment variables |
| 8 | XSS or clickjacking on the dashboard | API text rendered as React text only (tested with injected `<img onerror>`); strict Content-Security-Policy, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: no-referrer`; no CORS, same origin only | The admin key sits in `sessionStorage`, so a successful XSS could read it. CSP allows inline *styles* because the chart library needs them |
| 9 | Abuse and denial of service | Request size limits (prompt 20,000 characters, 20 documents of 50,000 each) | No rate limiting or quotas. A caller can burn your Gemini quota. `/api/chain` re-reads the whole log, so it is slow on very large logs |
| 10 | Secrets leaking through logs or errors | Only the error *type* is logged for upstream failures; responses use fixed messages; request bodies and keys are never logged; the key travels in a header, never a URL | Uvicorn access logs record URLs and query strings (for example the rule filter); fine today, but do not put sensitive values in query parameters |
| 11 | The guard fails and traffic flows unprotected | Fail closed: if the audit write fails the reply is withheld (503); provider errors give a safe 502 | A database outage takes the guard down. Because the model call precedes the audit write, a failed audit still costs a model call |
| 12 | Insecure defaults or leaked config | Compose requires every secret (no defaults); `.env` is git-ignored; Postgres is not published to the host; ports bind to 127.0.0.1; containers run as non-root | The `testpw` password in CI and in the docs is a throwaway for test databases. **There is no TLS** in this setup: put a TLS-terminating reverse proxy in front before exposing it |
| 13 | Vulnerable dependencies | Few dependencies, each justified in `docs/DECISIONS.md`; the dashboard uses a lockfile | Python dependencies are version-ranged, not locked. No automated vulnerability scanning or SBOM |

## Explicitly out of scope

- A malicious admin, or an attacker with full control of the host or database.
- What Gemini does with the (redacted) text: its retention and training policies are the provider's.
- Multi-turn attacks: the guard judges each call alone and keeps no conversation state.
- Images, files and other non-text inputs.
- Output quality, factual accuracy, bias and toxicity.
- Legal compliance of any kind.

## If I had more time (in order)

1. Anchor the chain head outside the database (a signed daily export or a write-once store).
2. Rate limiting and per-key quotas; key rotation and per-key audit identity.
3. A database trigger that rejects UPDATE and DELETE on `audit_events`.
4. Name and address detection (a small NER model), evaluated honestly.
5. A learned injection classifier as a second layer, with the same labelled eval discipline.
6. Lock the Python dependencies and add vulnerability scanning to CI.
