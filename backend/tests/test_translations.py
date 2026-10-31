from __future__ import annotations

from pathlib import Path

from apps.core.management.commands.check_translations import catalog_errors, parse_catalog
from django.core.management import call_command
from django.utils.translation import gettext, override

PO_HEADER = (
    'msgid ""\n'
    'msgstr ""\n'
    '"Project-Id-Version: Mawid\\n"\n'
    '"Language: ar\\n"\n'
    '"MIME-Version: 1.0\\n"\n'
    '"Content-Type: text/plain; charset=UTF-8\\n"\n'
    '"Content-Transfer-Encoding: 8bit\\n"\n'
)


def _write_po(path: Path, *blocks: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PO_HEADER + "\n\n" + "\n\n".join(blocks) + "\n", encoding="utf-8")
    return path


def test_parse_catalog_detects_untranslated(tmp_path: Path) -> None:
    path = _write_po(
        tmp_path / "ar" / "LC_MESSAGES" / "django.po",
        'msgid "Hello"\nmsgstr "مرحبا"',
        'msgid "Missing"\nmsgstr ""',
    )
    entries = parse_catalog(path)
    assert len(entries) == 2
    errors = catalog_errors("ar", entries)
    assert any("untranslated" in error and "Missing" in error for error in errors)


def test_parse_catalog_detects_fuzzy(tmp_path: Path) -> None:
    path = _write_po(
        tmp_path / "ar" / "LC_MESSAGES" / "django.po",
        '#, fuzzy\nmsgid "Hi"\nmsgstr "مرحبا"',
    )
    errors = catalog_errors("ar", parse_catalog(path))
    assert any("fuzzy" in error for error in errors)


def test_parse_catalog_detects_placeholder_mismatch(tmp_path: Path) -> None:
    path = _write_po(
        tmp_path / "ar" / "LC_MESSAGES" / "django.po",
        'msgid "Name %(name)s"\nmsgstr "الاسم %(full_name)s"',
    )
    errors = catalog_errors("ar", parse_catalog(path))
    assert any("placeholder mismatch" in error for error in errors)


def test_parse_catalog_detects_obsolete(tmp_path: Path) -> None:
    path = _write_po(
        tmp_path / "ar" / "LC_MESSAGES" / "django.po",
        '#~ msgid "Old"\n#~ msgstr "قديم"',
    )
    errors = catalog_errors("ar", parse_catalog(path))
    assert any("obsolete" in error for error in errors)


def test_check_translations_passes_on_committed_catalogs() -> None:
    call_command("check_translations", skip_source_check=True)


def test_arabic_translation_is_available() -> None:
    with override("ar"):
        assert gettext("The appointment was not found.") == "لم يتم العثور على الموعد."


def test_english_translation_is_identity() -> None:
    with override("en"):
        assert gettext("Staff") == "Staff"
