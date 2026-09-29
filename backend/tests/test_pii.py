from app.pii import contains_pii, redact_pii


def test_redacts_ssn():
    assert redact_pii("my ssn is 123-45-6789") == "my ssn is [REDACTED_SSN]"


def test_redacts_email():
    assert (
        redact_pii("reach me at jane.doe@example.com please")
        == "reach me at [REDACTED_EMAIL] please"
    )


def test_redacts_phone():
    result = redact_pii("call me at (555) 123-4567 tomorrow")
    assert "[REDACTED_PHONE]" in result
    assert "555" not in result


def test_redacts_card_number():
    result = redact_pii("my card number is 4111 1111 1111 1111")
    assert "[REDACTED_CARD_NUMBER]" in result
    assert "4111" not in result


def test_leaves_ordinary_text_untouched():
    text = "I'm not sure this fits my budget right now."
    assert redact_pii(text) == text


def test_contains_pii_true_and_false():
    assert contains_pii("email me at a@b.com") is True
    assert contains_pii("no personal info here") is False


def test_multiple_pii_types_in_one_string():
    text = "SSN 123-45-6789, email a@b.com, phone 555-123-4567"
    redacted = redact_pii(text)
    assert "[REDACTED_SSN]" in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
