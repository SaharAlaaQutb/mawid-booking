import ast
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command

HEADER_DATE = "2026-10-31 00:00+0000"
PLACEHOLDER = re.compile(r"%\((\w+)\)s")


@dataclass(frozen=True)
class Entry:
    msgid: str
    msgstr: str
    fuzzy: bool
    obsolete: bool


def _unquote(raw: str) -> str:
    return ast.literal_eval(f'"{raw}"')


def _line_content(line: str) -> str:
    content = line.lstrip()
    if content.startswith("#~ "):
        content = content[len("#~ ") :]
    return content


def _extract(block: str, keyword: str) -> str | None:
    value: str | None = None
    collecting = False
    for line in block.splitlines():
        content = _line_content(line)
        if collecting:
            if content.startswith('"') and content.endswith('"'):
                value = (value or "") + _unquote(content[1:-1])
                continue
            break
        if content.startswith(f"{keyword} "):
            raw = content[len(keyword) + 1 :]
            if raw.startswith('"') and raw.endswith('"'):
                value = _unquote(raw[1:-1])
                collecting = True
    return value


def parse_catalog(path: Path) -> list[Entry]:
    entries: list[Entry] = []
    blocks = re.split(r"\n{2,}", path.read_text(encoding="utf-8").strip())
    for block in blocks:
        if "Project-Id-Version" in block:
            continue
        msgid = _extract(block, "msgid")
        if msgid is None:
            continue
        msgstr = _extract(block, "msgstr")
        entries.append(
            Entry(
                msgid=msgid,
                msgstr=msgstr or "",
                fuzzy=any(line.startswith("#,") and "fuzzy" in line for line in block.splitlines()),
                obsolete=any(line.startswith("#~") for line in block.splitlines()),
            )
        )
    return entries


def catalog_errors(locale: str, entries: list[Entry]) -> list[str]:
    errors: list[str] = []
    for entry in entries:
        if entry.obsolete:
            errors.append(f"{locale}: obsolete entry {entry.msgid!r}")
            continue
        if entry.fuzzy:
            errors.append(f"{locale}: fuzzy entry {entry.msgid!r}")
        if not entry.msgstr:
            errors.append(f"{locale}: untranslated entry {entry.msgid!r}")
        if set(PLACEHOLDER.findall(entry.msgid)) != set(PLACEHOLDER.findall(entry.msgstr)):
            errors.append(f"{locale}: placeholder mismatch for {entry.msgid!r}")
    return errors


def normalize_header(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r'"POT-Creation-Date: [^"]*\\n"', f'"POT-Creation-Date: {HEADER_DATE}\\\\n"', text
    )
    text = re.sub(r'"PO-Revision-Date: [^"]*\\n"', f'"PO-Revision-Date: {HEADER_DATE}\\\\n"', text)
    path.write_text(text, encoding="utf-8")


class Command(BaseCommand):
    help = "Regenerate and validate the backend translation catalogs."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--skip-source-check",
            action="store_true",
            help="Only validate the committed catalogs, without regenerating them.",
        )

    def handle(self, *args, **options) -> None:
        locale_root = Path(settings.LOCALE_PATHS[0])
        locales = [code for code, _ in settings.LANGUAGES]
        if not options["skip_source_check"]:
            call_command(
                "makemessages",
                locale=locales,
                no_location=True,
                no_wrap=True,
                verbosity=0,
            )
            for locale in locales:
                normalize_header(locale_root / locale / "LC_MESSAGES" / "django.po")
            self._check_source_changes(locale_root)

        catalogs = {}
        errors: list[str] = []
        for locale in locales:
            entries = parse_catalog(locale_root / locale / "LC_MESSAGES" / "django.po")
            catalogs[locale] = {entry.msgid for entry in entries}
            errors.extend(catalog_errors(locale, entries))

        keys = set.union(*catalogs.values())
        for locale, locale_keys in catalogs.items():
            for missing in sorted(keys - locale_keys):
                errors.append(f"{locale}: missing catalog key {missing!r}")

        if errors:
            raise CommandError("Translation check failed:\n" + "\n".join(errors))
        self.stdout.write(
            self.style.SUCCESS(f"Translation catalogs are complete for {', '.join(locales)}.")
        )

    def _check_source_changes(self, locale_root: Path) -> None:
        relative = locale_root.relative_to(settings.BASE_DIR)
        diff = subprocess.run(
            ["git", "diff", "--quiet", "--", str(relative)],
            cwd=settings.BASE_DIR,
            check=False,
        )
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "--", str(relative)],
            cwd=settings.BASE_DIR,
            check=False,
            capture_output=True,
            text=True,
        )
        if diff.returncode != 0 or untracked.stdout.strip():
            raise CommandError(
                "Translation catalogs are out of date; run makemessages and commit the changes."
            )
