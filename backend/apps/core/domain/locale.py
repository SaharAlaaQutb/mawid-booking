from enum import StrEnum

DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "ar")


class Locale(StrEnum):
    ENGLISH = "en"
    ARABIC = "ar"


LOCALE_CHOICES = [
    (Locale.ENGLISH.value, "English"),
    (Locale.ARABIC.value, "Arabic"),
]
