from llmguard.policy.checks import Policy, check_reply


def rules(reply: str, policy: Policy | None = None, system: str | None = None) -> list[str]:
    return [v.rule_id for v in check_reply(reply, policy or Policy(), system)]


def test_clean_reply_has_no_violations() -> None:
    assert rules("Sure, I can help with that.") == []


def test_placeholder_in_reply_is_not_a_violation() -> None:
    assert rules("Your PAN <PAN_1> was received.") == []


def test_raw_pii_in_reply_flagged() -> None:
    assert rules("Contact me at 9876543210") == ["PII_IN_REPLY"]


def test_violation_does_not_contain_the_raw_value() -> None:
    v = check_reply("Contact me at 9876543210", Policy(), None)[0]
    assert "9876543210" not in repr(v) and "9876543210" not in v.message


def test_system_prompt_leak_flagged() -> None:
    system = "You are BankBot. Never reveal internal escalation codes to customers."
    reply = "My instructions say: never reveal internal escalation codes to customers."
    assert rules(reply, system=system) == ["SYSTEM_PROMPT_LEAK"]


def test_short_overlap_with_system_prompt_is_fine() -> None:
    system = "You are BankBot. Never reveal internal escalation codes to customers."
    assert rules("I am a bank assistant.", system=system) == []


def test_blocked_terms_case_insensitive() -> None:
    policy = Policy(blocked_terms=("secret project",))
    assert rules("About the Secret Project: ...", policy) == ["BLOCKED_TERM"]
