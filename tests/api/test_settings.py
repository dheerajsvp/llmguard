import pytest

from llmguard.api.settings import Settings, SettingsError

CHAT = "chat-key-0123456789abcdef"
ADMIN = "admin-key-0123456789abcdef"


def env(**overrides: str) -> dict[str, str]:
    base = {
        "LLMGUARD_DATABASE_URL": "postgresql+psycopg://u:p@db/x",
        "LLMGUARD_API_KEYS": CHAT,
        "LLMGUARD_ADMIN_KEYS": ADMIN,
    }
    base.update(overrides)
    return base


def test_valid_env_loads_with_safe_defaults() -> None:
    s = Settings.from_env(env())
    assert s.chat_keys == {CHAT} and s.admin_keys == {ADMIN}
    assert s.provider == "gemini" and s.restore_types == frozenset()


def test_multiple_keys_and_whitespace() -> None:
    other = "another-chat-key-0123456789"
    s = Settings.from_env(env(LLMGUARD_API_KEYS=f" {CHAT} , {other} "))
    assert s.chat_keys == {CHAT, other}


@pytest.mark.parametrize(
    "missing", ["LLMGUARD_DATABASE_URL", "LLMGUARD_API_KEYS", "LLMGUARD_ADMIN_KEYS"]
)
def test_missing_required_setting_refuses_to_start(missing: str) -> None:
    e = env()
    del e[missing]
    with pytest.raises(SettingsError, match=missing):
        Settings.from_env(e)


def test_short_key_rejected() -> None:
    with pytest.raises(SettingsError, match="16"):
        Settings.from_env(env(LLMGUARD_API_KEYS="short"))


def test_chat_and_admin_keys_must_differ() -> None:
    with pytest.raises(SettingsError, match="overlap"):
        Settings.from_env(env(LLMGUARD_ADMIN_KEYS=CHAT))


def test_unknown_provider_rejected() -> None:
    with pytest.raises(SettingsError, match="PROVIDER"):
        Settings.from_env(env(LLMGUARD_PROVIDER="openai"))


def test_restore_types_parsed_and_uppercased() -> None:
    s = Settings.from_env(env(LLMGUARD_RESTORE_TYPES="phone, email"))
    assert s.restore_types == {"PHONE", "EMAIL"}


def test_error_message_never_contains_the_key() -> None:
    with pytest.raises(SettingsError) as exc:
        Settings.from_env(env(LLMGUARD_API_KEYS="short"))
    assert "short" not in str(exc.value).replace("shorter", "")
