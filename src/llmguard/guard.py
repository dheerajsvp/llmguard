"""Guard: the library entry point that wraps one LLM call."""

from dataclasses import dataclass, field

from llmguard.pii.redactor import redact, restore
from llmguard.policy.checks import Policy, Violation, check_reply
from llmguard.providers.base import Provider

BLOCKED_REPLY = "[Response withheld by llmguard policy]"


@dataclass
class GuardResult:
    reply: str
    blocked: bool
    violations: list[Violation] = field(default_factory=list)
    redacted_prompt: str = ""
    # entity type -> how many distinct values were redacted. Counts only, no values.
    redactions: dict[str, int] = field(default_factory=dict)


class Guard:
    def __init__(self, provider: Provider, policy: Policy | None = None) -> None:
        self.provider = provider
        self.policy = policy or Policy()

    def run(self, prompt: str, system: str | None = None) -> GuardResult:
        # 1. Redact. The placeholder map stays in this function's memory only.
        redaction = redact(prompt)
        counts: dict[str, int] = {}
        for placeholder in redaction.mapping:
            kind = placeholder[1:].rsplit("_", 1)[0]
            counts[kind] = counts.get(kind, 0) + 1

        # 2. Call the model with the cleaned prompt.
        raw_reply = self.provider.generate(redaction.text, system)

        # 3. Check the reply before restoring anything.
        violations = check_reply(raw_reply, self.policy, system)
        if violations and self.policy.block_on_violation:
            return GuardResult(BLOCKED_REPLY, True, violations, redaction.text, counts)

        # 4. Restore only the placeholder types the policy allows.
        reply = restore(raw_reply, redaction.mapping, set(self.policy.restore_types))
        return GuardResult(reply, False, violations, redaction.text, counts)
