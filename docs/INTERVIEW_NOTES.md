# Interview notes

For explaining llmguard out loud. Each answer is meant to be said in your own words, not read.
The honest follow-ups matter most: interviewers trust people who know their project's limits.

## The 30-second pitch

> "llmguard sits between an app and an LLM. Before a message reaches Gemini it hides Indian
> personal data such as PAN and Aadhaar, and it blocks prompt-injection attempts. It checks the
> reply too. Every call is written to a tamper-evident audit log in Postgres that never stores
> the real data, and there's a React dashboard to see what's happening. I built it test-first and
> measured the detectors honestly, including where they fail."

## Numbers to know (as of the last run)

| Thing | Value |
|---|---|
| Python tests / dashboard tests | 144 (with Postgres) / 45 |
| Injection eval, dev (n=41) | precision 0.95, recall 0.88, false-positive rate 0.06 |
| Injection eval, test (n=39) | precision 0.86, recall 0.90, false-positive rate 0.16 |
| PII eval (synthetic, 200 per type) | 1.000 precision and recall on all six types |
| PII types | PAN, Aadhaar, phone, UPI, email, card |

If asked "is 0.90 recall good?": **say it's optimistic.** The same author wrote the rules and both
sets, the test split isn't blind, and there are only about 20 attacks per split, so one case moves
recall by 5 points. The PII scores come from a generator that shares the detector's assumptions.

## Design choices: what to say, and what they'll ask next

### Why regex plus a checksum for PII, not an ML model?
Regex finds the *shape*; the checksum filters out lookalikes (a random 12-digit order number
passes Verhoeff only about 1 time in 10). It's fast, deterministic, explainable and needs no
training data. **Follow-up: what does it miss?** Names, addresses, odd formatting. A real
version would add a small NER model, evaluated the same honest way.

### What is a checksum?
A built-in typo detector: the last digit is computed from the others, so it must agree with them.
Luhn for cards, Verhoeff for Aadhaar (Verhoeff also catches swapped neighbouring digits).
**Follow-up: does a valid checksum mean the Aadhaar is real?** No, only well-formed.

### Why placeholders like `<PAN_1>`?
The model can still reason about the text ("the PAN you gave me") without seeing the value. The
same value always gets the same placeholder, so replies stay coherent. The map lives only in
memory for one request.

### Why is restoring PII off by default?
Restoring puts private data back into the reply, which re-exposes it. So each type must be allowed
explicitly (`restore_types`), and nothing is restored when a reply is blocked.

### Why check the reply *before* restoring?
At that point any raw PII in the reply can only have come from the model itself, which is a
violation. After restoring, you couldn't tell the difference.

### Why block *before* calling the model?
Saves cost and prevents exposure. An injection hit returns a refusal and the model never sees it.

### Why rules for injection, not an ML classifier?
Simple, auditable, and I could explain every rule. I was honest about the trade-off: it catches
known phrasings and misses paraphrase and other languages. **Follow-up: how would you improve it?**
Add a learned classifier as a second layer and evaluate it on the same labelled set, reporting
precision and recall.

### Why scan documents separately from the user's message?
Indirect injection is a different threat: an attacker hides instructions in a web page or PDF the
app retrieves. Some rules only make sense for documents ("note to the AI", "email the data to...").
For a user, "email this to bob@x.com" is a normal request, so that rule applies to documents only.

### What did the evaluation teach you?
It caught a real bug: a spaced 16-digit card number could have its first 12 digits claimed as an
Aadhaar, giving 9 card misses and 9 Aadhaar false positives. I fixed it with a regression test. It
also exposed a bug in my own eval generator. Good evals find mistakes in the evaluator too.

### How does the hash chain work?
Each record stores the hash of the previous one: `hash = sha256(prev_hash + the record)`. Edit an
old record and its hash no longer matches; fix that hash and the *next* record's link breaks. So an
edit is detectable by walking the chain. **Follow-up: what are the limits?** If someone rewrites
the whole chain from the edit onward, or deletes the newest rows, it still verifies. You defend
against that by copying the latest hash somewhere the attacker can't reach, which I documented but
did not automate.

### Why an advisory lock?
Two requests at once could both read the same "latest" row and both extend it, forking the chain.
The Postgres advisory lock makes appends take turns. I proved it matters: with the lock removed, my
concurrency test fails with duplicate sequence numbers.

### Why fail closed on audit failure?
An unaudited call is worse than a failed one for a governance tool. The trade-off is that a
database outage takes the guard down, and the model call already happened, so you pay for a reply
nobody sees.

### Why not store the prompt?
It would turn the audit log into a PII store. I store counts, rule ids and a hash of the
*redacted* prompt. **Follow-up: isn't a hash reversible?** For short, guessable text it can be
confirmed by guessing, which is why I hash the redacted prompt, never the raw one.

### Why FastAPI, and why plain `def` endpoints?
Typed validation, automatic docs, light enough for a proxy. The Gemini call blocks, and FastAPI runs
plain functions in a thread pool, so one slow call doesn't freeze the server. `async def` would block
the event loop.

### Why two API key types?
A caller who can chat shouldn't be able to read the audit log. The server refuses to start if the
sets overlap, keys are short, or they're missing. Wrong role gets 403, unknown key gets 401. Keys are
compared in constant time.

### Why is a blocked request HTTP 200?
The request was handled correctly; the body says `blocked: true` with the rule ids. Real failures use
502 (model failed) and 503 (audit failed), with fixed messages that never echo the prompt.

### Why no CORS on the API?
The dashboard calls `/api` on its own origin, and nginx (or Vite in development) forwards it. So no
other website's JavaScript can call the API from a browser.

### Why is the admin key in sessionStorage?
It survives a reload but is cleared when the tab closes; localStorage would keep it on disk. It's
only ever sent in a header. **Follow-up: what if there's XSS?** Then it could be read. That's why API
text is rendered as plain text (tested with injected HTML), and there's a strict
Content-Security-Policy.

### Why that chart design?
The story is "how much was blocked", so blocked is the accent colour and everything else is grey
(an *emphasis* chart), not an arbitrary two-colour split. Top rules is ranked bars in one colour,
because length already carries the value. Every chart has a table view, so no value depends on hover.

### How did you test it?
Test-first throughout. I also **broke the code on purpose** to check the tests notice: removing the
lock, logging raw error text, accepting any key, storing the key in localStorage, rendering text as
HTML. Once a "no leaks" test passed under mutation because it checked the wrong thing; I fixed the
test. That's how I know the security tests aren't decoration.

## Things you should NOT claim

- That it prevents prompt injection. It **reduces** risk against known phrasings.
- That it makes anyone DPDP or GDPR compliant.
- That the audit log is tamper-proof. It's tamper-**evident**, with the limits above.
- That the real Gemini integration is production-tested. `GeminiProvider` has never been run against
  the live API; every automated test uses the fake provider.
- That the eval numbers generalise. Small, partly synthetic, and not blind.

## "What would you do next?" (pick two)

1. Anchor the chain head outside the database.
2. Rate limiting, key rotation and per-key identity.
3. A learned injection classifier as a second layer, with the same eval discipline.
4. Name and address detection.
5. A database trigger that rejects UPDATE and DELETE on the audit table.
