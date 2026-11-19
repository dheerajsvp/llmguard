from llmguard.pii.validators import luhn_valid, verhoeff_check_digit, verhoeff_valid


def test_verhoeff_known_example() -> None:
    # Classic worked example: 236 + check digit 3
    assert verhoeff_check_digit("236") == "3"
    assert verhoeff_valid("2363")


def test_verhoeff_detects_single_digit_error() -> None:
    assert not verhoeff_valid("2364")


def test_verhoeff_detects_adjacent_transposition() -> None:
    assert not verhoeff_valid("2633")


def test_verhoeff_roundtrip_for_12_digit_numbers() -> None:
    body = "23456789012"
    assert verhoeff_valid(body + verhoeff_check_digit(body))


def test_luhn_valid_test_card() -> None:
    assert luhn_valid("4111111111111111")


def test_luhn_invalid() -> None:
    assert not luhn_valid("4111111111111112")


def test_luhn_rejects_non_digits_and_empty() -> None:
    assert not luhn_valid("")
    assert not luhn_valid("4111x11111111111")
