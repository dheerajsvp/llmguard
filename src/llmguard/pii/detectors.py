"""Find PII spans in text. Each detector is a regex plus an optional validator."""

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from llmguard.pii.validators import luhn_valid, verhoeff_valid


@dataclass(frozen=True)
class Entity:
    """A detected PII span. `value` is hidden from repr so it cannot leak into logs."""

    type: str
    start: int
    end: int
    value: str = field(repr=False)


@dataclass(frozen=True)
class _Rule:
    type: str
    pattern: re.Pattern[str]
    validator: Callable[[str], bool] | None = None


def _digits(s: str) -> str:
    return re.sub(r"[\s-]", "", s)


# Order = priority when two matches overlap (earlier wins). Checksummed types come
# first because a passing checksum is strong evidence.
_RULES: tuple[_Rule, ...] = (
    _Rule(
        "AADHAAR",
        # The extra lookarounds stop us matching 12 digits of a longer grouped number
        # (e.g. the first three groups of a spaced 16-digit card).
        re.compile(r"(?<!\d)(?<!\d[ -])[2-9]\d{3}([ -]?)\d{4}\1\d{4}(?!\d)(?![ -]\d{4}\b)"),
        lambda s: verhoeff_valid(_digits(s)),
    ),
    _Rule(
        "CARD",
        re.compile(r"(?<!\d)\d{4}([ -]?)\d{4}\1\d{4}\1\d{1,7}(?!\d)"),
        lambda s: 13 <= len(_digits(s)) <= 19 and luhn_valid(_digits(s)),
    ),
    # PAN: 5 letters, 4 digits, 1 letter. The 4th letter encodes the holder type.
    _Rule("PAN", re.compile(r"\b[A-Z]{3}[PCHABGJLFT][A-Z]\d{4}[A-Z]\b")),
    _Rule("EMAIL", re.compile(r"\b[\w.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b")),
    # UPI ID: handle@bank with no dot after the @ (a dot would make it an email).
    _Rule("UPI", re.compile(r"\b[\w.-]{2,}@[A-Za-z][A-Za-z0-9]{1,63}\b(?!\.[A-Za-z])")),
    # Indian mobile: optional +91 / 91 / 0 prefix, then 10 digits starting 6-9.
    _Rule(
        "PHONE",
        re.compile(r"(?<![\w+])(?:(?:\+91|91|0)[ -]?)?[6-9]\d{4}[ -]?\d{5}(?!\d)"),
    ),
)

PRIORITY: tuple[str, ...] = tuple(r.type for r in _RULES)


def detect(text: str) -> list[Entity]:
    """Return non-overlapping entities sorted by position."""
    candidates: list[tuple[int, int, Entity]] = []
    for rank, rule in enumerate(_RULES):
        for m in rule.pattern.finditer(text):
            value = m.group(0)
            if rule.validator and not rule.validator(value):
                continue
            candidates.append(
                (rank, -(m.end() - m.start()), Entity(rule.type, m.start(), m.end(), value))
            )

    # Greedy overlap resolution: best priority first, then longest span.
    accepted: list[Entity] = []
    for _, _, ent in sorted(candidates, key=lambda c: (c[0], c[1])):
        if all(ent.end <= a.start or ent.start >= a.end for a in accepted):
            accepted.append(ent)
    return sorted(accepted, key=lambda e: e.start)
