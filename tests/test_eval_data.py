import json
from pathlib import Path

EVAL = Path(__file__).resolve().parent.parent / "eval" / "injection.jsonl"


def load() -> list[dict[str, object]]:
    return [json.loads(line) for line in EVAL.read_text(encoding="utf-8").splitlines() if line]


def test_injection_eval_is_well_formed() -> None:
    rows = load()
    assert len({r["id"] for r in rows}) == len(rows)
    for r in rows:
        assert r["split"] in {"dev", "test"}
        assert r["label"] in {0, 1}
        assert r["source"] in {"user", "document"}
        assert isinstance(r["text"], str) and r["text"]


def test_each_split_has_both_classes_and_hard_cases() -> None:
    rows = load()
    for split in ("dev", "test"):
        part = [r for r in rows if r["split"] == split]
        assert sum(r["label"] == 1 for r in part) >= 10
        assert sum(r["label"] == 0 for r in part) >= 10
        assert any(r["category"] == "benign_hard" for r in part)
