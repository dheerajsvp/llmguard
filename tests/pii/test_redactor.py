from llmguard.pii.redactor import redact, restore
from llmguard.pii.validators import verhoeff_check_digit

# All values below are synthetic.
AADHAAR_BODY = "23456789012"
AADHAAR = AADHAAR_BODY + verhoeff_check_digit(AADHAAR_BODY)
AADHAAR_SPACED = f"{AADHAAR[:4]} {AADHAAR[4:8]} {AADHAAR[8:]}"
BAD_AADHAAR = AADHAAR[:-1] + str((int(AADHAAR[-1]) + 1) % 10)


def types(text: str) -> list[str]:
    return [e.type for e in redact(text).entities]


def test_pan_redacted() -> None:
    r = redact("My PAN is ABCPE1234F, thanks")
    assert r.text == "My PAN is <PAN_1>, thanks"
    assert r.mapping == {"<PAN_1>": "ABCPE1234F"}


def test_pan_wrong_shape_not_redacted() -> None:
    assert types("ABCXE1234F") == []  # 4th letter X is not a valid holder type
    assert types("ABCPE12345") == []


def test_aadhaar_valid_redacted_plain_and_spaced() -> None:
    assert redact(f"id {AADHAAR}").text == "id <AADHAAR_1>"
    assert redact(f"id {AADHAAR_SPACED}").text == "id <AADHAAR_1>"


def test_aadhaar_bad_checksum_not_redacted() -> None:
    assert "AADHAAR" not in types(f"order {BAD_AADHAAR}")


def test_phone_formats() -> None:
    for number in ["9876543210", "+91 98765 43210", "+91-9876543210", "09876543210"]:
        assert types(f"call {number} now") == ["PHONE"], number


def test_phone_not_starting_6_to_9_not_redacted() -> None:
    assert types("ref 1234567890") == []


def test_email_redacted() -> None:
    assert redact("mail a.b@example.co.in please").text == "mail <EMAIL_1> please"


def test_upi_redacted_and_not_confused_with_email() -> None:
    assert redact("pay rahul@oksbi now").text == "pay <UPI_1> now"
    assert types("rahul@example.com") == ["EMAIL"]


def test_card_valid_redacted_with_separators() -> None:
    assert redact("card 4111 1111 1111 1111").text == "card <CARD_1>"
    assert redact("card 4111-1111-1111-1111").text == "card <CARD_1>"


def test_card_failing_luhn_not_redacted() -> None:
    assert types("number 4111111111111112") == []


def test_same_value_same_placeholder_different_value_new_number() -> None:
    r = redact("ABCPE1234F then ABCPE1234F then QWEPR5678Z")
    assert r.text == "<PAN_1> then <PAN_1> then <PAN_2>"
    assert len(r.mapping) == 2


def test_counters_are_per_type() -> None:
    r = redact("ABCPE1234F and 9876543210")
    assert r.text == "<PAN_1> and <PHONE_1>"


def test_overlap_aadhaar_beats_phone() -> None:
    # A 12-digit valid Aadhaar must not be partly eaten by the phone rule.
    body = "98765432101"
    number = body + verhoeff_check_digit(body)
    assert types(f"x {number} y") == ["AADHAAR"]


def test_restore_roundtrip() -> None:
    original = f"PAN ABCPE1234F, phone 9876543210, aadhaar {AADHAAR_SPACED}"
    r = redact(original)
    assert "ABCPE1234F" not in r.text
    assert restore(r.text, r.mapping) == original


def test_restore_only_selected_types() -> None:
    r = redact("ABCPE1234F 9876543210")
    out = restore(r.text, r.mapping, allowed_types={"PHONE"})
    assert out == "<PAN_1> 9876543210"


def test_no_pii_returns_text_unchanged() -> None:
    r = redact("Hello, how are you?")
    assert r.text == "Hello, how are you?"
    assert r.entities == [] and r.mapping == {}


def test_entity_repr_does_not_leak_raw_value() -> None:
    r = redact("ABCPE1234F")
    assert "ABCPE1234F" not in repr(r.entities[0])


def test_spaced_card_is_not_split_into_aadhaar_prefix() -> None:
    # Build a card whose first 12 digits happen to be a *valid* Aadhaar, so the
    # Aadhaar rule would wrongly claim them if it ignored the surrounding digits.
    from llmguard.pii.validators import luhn_valid

    first12 = "42345678901" + verhoeff_check_digit("42345678901")
    card = next(first12 + "345" + str(d) for d in range(10) if luhn_valid(first12 + "345" + str(d)))
    spaced = " ".join(card[i : i + 4] for i in range(0, 16, 4))
    assert redact(f"card {spaced}").text == "card <CARD_1>"
