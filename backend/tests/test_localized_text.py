from apps.core.domain.localized_text import LocalizedText


def test_returns_requested_locale() -> None:
    text = LocalizedText(ar="مرحبا", en="Hello")

    assert text.for_locale("ar") == "مرحبا"
    assert text.for_locale("en") == "Hello"
    assert text.for_locale("ar-SA") == "مرحبا"


def test_falls_back_to_the_other_language() -> None:
    assert LocalizedText(ar="مرحبا").for_locale("en") == "مرحبا"
    assert LocalizedText(en="Hello").for_locale("ar") == "Hello"


def test_unknown_locale_uses_default() -> None:
    assert LocalizedText(ar="مرحبا", en="Hello").for_locale("fr") == "Hello"


def test_strips_whitespace_and_detects_empty() -> None:
    text = LocalizedText(ar="  ", en="  Hello  ")

    assert text.ar == ""
    assert text.en == "Hello"
    assert not text.is_empty()
    assert text.as_dict() == {"ar": "", "en": "Hello"}
    assert LocalizedText().is_empty()
