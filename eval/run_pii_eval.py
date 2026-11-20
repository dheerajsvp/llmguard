"""Evaluate PII detection on synthetic, seeded data.

Usage: python eval/run_pii_eval.py [--seed 0] [--n 200]

Positives are generated from templates with valid synthetic values. Negatives are
"near misses": strings that look like an identifier but fail its rules. A detection
counts as correct only if both type and exact matched string equal what we inserted.

Caveat: data and detector were written by the same author, so recall here is
optimistic. Real-world text will be messier.
"""

import argparse
import random
import string
from collections import Counter

from llmguard.pii.detectors import detect
from llmguard.pii.validators import luhn_valid, verhoeff_check_digit, verhoeff_valid

TEMPLATES = ["My {t} is {v}.", "Please update {v} on my account", "ref: {v}, thanks", "{v}"]


def digits(rng: random.Random, n: int, first: str = "0123456789") -> str:
    return rng.choice(first) + "".join(rng.choice(string.digits) for _ in range(n - 1))


def luhn_check_digit(body: str) -> str:
    return next(str(d) for d in range(10) if luhn_valid(body + str(d)))


def make_positive(rng: random.Random, kind: str) -> str:
    if kind == "PAN":
        letters = string.ascii_uppercase
        return (
            "".join(rng.choice(letters) for _ in range(3))
            + rng.choice("PCHABGJLFT")
            + rng.choice(letters)
            + digits(rng, 4)
            + rng.choice(letters)
        )
    if kind == "AADHAAR":
        body = digits(rng, 11, "23456789")
        n = body + verhoeff_check_digit(body)
        sep = rng.choice(["", " ", "-"])
        return sep.join([n[:4], n[4:8], n[8:]])
    if kind == "PHONE":
        n = digits(rng, 10, "6789")
        return rng.choice(["", "+91 ", "+91-", "0", "91 "]) + n
    if kind == "UPI":
        handle = "".join(rng.choice(string.ascii_lowercase) for _ in range(rng.randint(4, 9)))
        return f"{handle}@{rng.choice(['okaxis', 'oksbi', 'ybl', 'paytm', 'upi'])}"
    if kind == "EMAIL":
        user = "".join(rng.choice(string.ascii_lowercase) for _ in range(rng.randint(4, 9)))
        return f"{user}@{rng.choice(['example.com', 'mail.example.co.in', 'corp.example.org'])}"
    if kind == "CARD":
        body = digits(rng, 15, "456")
        n = body + luhn_check_digit(body)
        sep = rng.choice(["", " ", "-"])
        return sep.join(n[i : i + 4] for i in range(0, 16, 4))
    raise ValueError(kind)


def make_negative(rng: random.Random) -> str:
    kind = rng.choice(["aadhaar_bad", "card_bad", "pan_bad", "phone_bad", "order_id", "plain"])
    if kind == "aadhaar_bad":
        while True:
            n = digits(rng, 12, "23456789")
            if not verhoeff_valid(n):
                return f"Order number {n}"
    if kind == "card_bad":
        while True:
            n = digits(rng, 16, "456")
            if not luhn_valid(n):
                return f"Tracking {n}"
    if kind == "pan_bad":
        # 4th letter is deliberately outside the valid PAN holder-type set.
        bad4 = rng.choice([c for c in string.ascii_uppercase if c not in "PCHABGJLFT"])
        head = "".join(rng.choice(string.ascii_uppercase) for _ in range(3))
        return f"Code {head}{bad4}{rng.choice(string.ascii_uppercase)}{digits(rng, 4)}Z"
    if kind == "phone_bad":
        return f"Call {digits(rng, 10, '12345')}"
    if kind == "order_id":
        return f"Invoice INV-{digits(rng, 6)} total 1,299.00"
    return rng.choice(
        ["Hello, how are you?", "Meet me at 5pm @ the cafe", "Follow @rahul_k on social"]
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n", type=int, default=200, help="positives per type, and total negatives")
    args = ap.parse_args()
    rng = random.Random(args.seed)
    kinds = ["PAN", "AADHAAR", "PHONE", "UPI", "EMAIL", "CARD"]

    tp, fp, fn = Counter(), Counter(), Counter()
    for kind in kinds:
        for _ in range(args.n):
            value = make_positive(rng, kind)
            text = rng.choice(TEMPLATES).format(t=kind.lower(), v=value)
            found = {(e.type, e.value) for e in detect(text)}
            if (kind, value) in found:
                tp[kind] += 1
            else:
                fn[kind] += 1
            for t, _v in found - {(kind, value)}:
                fp[t] += 1
    neg_fp = 0
    for _ in range(args.n):
        found = detect(make_negative(rng))
        neg_fp += bool(found)
        for e in found:
            fp[e.type] += 1

    print(f"seed={args.seed} positives/type={args.n} negatives={args.n}")
    print(f"{'type':8} {'TP':>4} {'FP':>4} {'FN':>4} {'precision':>10} {'recall':>7}")
    for k in kinds:
        p = tp[k] / (tp[k] + fp[k]) if tp[k] + fp[k] else float("nan")
        r = tp[k] / (tp[k] + fn[k])
        print(f"{k:8} {tp[k]:>4} {fp[k]:>4} {fn[k]:>4} {p:>10.3f} {r:>7.3f}")
    print(f"negative texts with any false detection: {neg_fp}/{args.n}")


if __name__ == "__main__":
    main()
