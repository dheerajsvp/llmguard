"""Evaluate the injection detector on eval/injection.jsonl.

Usage: python eval/run_injection_eval.py [--split dev|test|all] [--misses]

A text counts as "flagged" if scan() returns any finding for its source.
Metrics are per split. Positive = attack.
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from llmguard.injection.detector import scan

DATA = Path(__file__).parent / "injection.jsonl"


def ratio(num: int, den: int) -> str:
    return f"{num / den:.2f}" if den else "n/a"


def report(split: str, rows: list[dict[str, object]], show_misses: bool) -> None:
    tp = fp = fn = tn = 0
    by_cat: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # category -> [caught, total]
    misses: list[str] = []
    for r in rows:
        flagged = bool(scan(str(r["text"]), r["source"]))  # type: ignore[arg-type]
        label = r["label"] == 1
        tp += flagged and label
        fp += flagged and not label
        fn += (not flagged) and label
        tn += (not flagged) and not label
        by_cat[str(r["category"])][1] += 1
        by_cat[str(r["category"])][0] += flagged == label
        if flagged != label:
            kind = "FN (missed attack)" if label else "FP (false alarm)"
            misses.append(f"  {r['id']} {kind} [{r['category']}]: {r['text']!r}")

    print(f"\n== {split}: n={len(rows)} (attacks={tp + fn}, benign={tn + fp}) ==")
    print(f"TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"precision={ratio(tp, tp + fp)} recall={ratio(tp, tp + fn)} FPR={ratio(fp, fp + tn)}")
    print(
        "correct per category: " + ", ".join(f"{k} {c}/{t}" for k, (c, t) in sorted(by_cat.items()))
    )
    if show_misses:
        print("\n".join(misses) or "  (no errors)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test", "all"], default="all")
    ap.add_argument("--misses", action="store_true", help="list every error")
    args = ap.parse_args()
    rows = [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines() if line]
    for split in ("dev", "test"):
        if args.split in (split, "all"):
            report(split, [r for r in rows if r["split"] == split], args.misses)


if __name__ == "__main__":
    main()
