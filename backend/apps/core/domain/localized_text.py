from dataclasses import dataclass

from apps.core.domain.locale import DEFAULT_LOCALE, SUPPORTED_LOCALES


@dataclass(frozen=True, slots=True)
class LocalizedText:
    ar: str = ""
    en: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "ar", self.ar.strip())
        object.__setattr__(self, "en", self.en.strip())

    def for_locale(self, locale: str) -> str:
        requested = locale.split("-", maxsplit=1)[0].lower()
        if requested not in SUPPORTED_LOCALES:
            requested = DEFAULT_LOCALE
        preferred, fallback = (self.ar, self.en) if requested == "ar" else (self.en, self.ar)
        return preferred or fallback

    def is_empty(self) -> bool:
        return not self.ar and not self.en

    def as_dict(self) -> dict[str, str]:
        return {"ar": self.ar, "en": self.en}
