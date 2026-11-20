"""Policy config and checks on the model's reply."""

import re
from dataclasses import dataclass

from llmguard.pii.detectors import detect

# A system-prompt leak is flagged when this many consecutive words from the
# system prompt appear verbatim in the reply. Short overlaps are normal language.
LEAK_WINDOW_WORDS = 6


@dataclass(frozen=True)
class Policy:
    # Placeholder types that may be put back into the reply, e.g. {"PHONE"}.
    # Default is empty: restoring PII is opt-in because it re-exposes it.
    restore_types: frozenset[str] | set[str] = frozenset()
    blocked_terms: tuple[str, ...] = ()
    # True: replace the reply with a refusal on any violation. False: just report it.
    block_on_violation: bool = True


@dataclass(frozen=True)
class Violation:
    rule_id: str
    message: str  # never includes raw values


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _leaks_system_prompt(reply: str, system: str) -> bool:
    sys_words, reply_text = _words(system), " ".join(_words(reply))
    n = LEAK_WINDOW_WORDS
    return any(" ".join(sys_words[i : i + n]) in reply_text for i in range(len(sys_words) - n + 1))


def check_reply(reply: str, policy: Policy, system: str | None) -> list[Violation]:
    violations: list[Violation] = []

    found = detect(reply)
    if found:
        kinds = sorted({e.type for e in found})
        violations.append(
            Violation(
                "PII_IN_REPLY", f"Reply contains unredacted PII of type(s): {', '.join(kinds)}"
            )
        )

    if system and _leaks_system_prompt(reply, system):
        violations.append(Violation("SYSTEM_PROMPT_LEAK", "Reply repeats the system prompt"))

    lowered = reply.lower()
    if any(term.lower() in lowered for term in policy.blocked_terms):
        violations.append(Violation("BLOCKED_TERM", "Reply contains a blocked term"))

    return violations
