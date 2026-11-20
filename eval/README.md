# Evaluation

All data is synthetic. Run from the repo root with the venv active.

```
python eval/run_injection_eval.py --misses
python eval/run_pii_eval.py --seed 0
```

## Prompt-injection detector (`injection.jsonl`)

80 hand-written texts: 41 `dev` + 39 `test`. Positive = attack. Includes hard negatives (benign text that
looks suspicious) and attacks designed to evade the rules (paraphrase, other languages, spaced letters).

| split | n  | TP | FP | FN | TN | precision | recall | FPR  |
|-------|----|----|----|----|----|-----------|--------|------|
| dev   | 41 | 21 | 1  | 3  | 16 | 0.95      | 0.88   | 0.06 |
| test  | 39 | 18 | 3  | 2  | 16 | 0.86      | 0.90   | 0.16 |

Errors on test:
- Missed attacks: a paraphrase ("set aside everything you were told") and a German attack.
- False alarms: "print a system message in Linux logs", "enable developer mode on my phone", and a benign
  document sentence "email the report to our manager at boss@..." (the document-only exfiltration rule).
- Dev also missed Spanish and spaced-out-letter attacks and flagged "ignore the previous instructions in the recipe".

### How much to trust these numbers
- **The test split is not blind.** The same author (an AI assistant) wrote the rules and both splits in one
  session, so the rules were shaped by having seen the test phrasings. Treat test numbers as optimistic.
- **Small n.** With ~20 attacks per split, one case moves recall by 5 points. Do not read 0.88 vs 0.90 as a difference.
- Phrasing is the author's, not real attackers'. Expect real-world recall to be lower.
- The detector flags *known phrasings*. Paraphrase and non-English attacks are an unfixed gap by design.

## PII detector (`run_pii_eval.py`)

Seeded generator: 200 valid synthetic positives per type plus 200 near-miss negatives (bad checksums,
wrong shapes, order numbers). Seeds 0, 1 and 2 all give precision = recall = 1.000 for every type and 0/200
false detections on negatives.

This says the detector is correct on the formats the generator produces, and nothing more:
generator and detector share the author's assumptions. Real text (OCR errors, odd spacing, names,
addresses, landline numbers) is out of scope and untested. Perfect scores here are a sanity check, not a claim.

The eval earned its keep once: a first run showed spaced 16-digit cards being split by the Aadhaar rule
(9 card misses, 9 Aadhaar false positives). Fixed with a regression test in `tests/pii/test_redactor.py`.
