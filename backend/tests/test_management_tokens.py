from datetime import UTC, datetime, timedelta

import pytest
from apps.bookings.domain.tokens import (
    MANAGEMENT_TOKEN_TTL_DAYS,
    build_management_link,
    hash_management_token,
    issue_management_token,
)

STARTS_AT = datetime(2026, 11, 2, 9, tzinfo=UTC)


def test_issues_hashed_token_with_expiry() -> None:
    issued = issue_management_token(STARTS_AT)

    assert issued.value
    assert issued.token_hash == hash_management_token(issued.value)
    assert issued.expires_at == STARTS_AT + timedelta(days=MANAGEMENT_TOKEN_TTL_DAYS)


def test_tokens_are_unique() -> None:
    first = issue_management_token(STARTS_AT)
    second = issue_management_token(STARTS_AT)

    assert first.value != second.value
    assert first.token_hash != second.token_hash


def test_token_requires_aware_start() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        issue_management_token(datetime(2026, 11, 2, 9))


def test_builds_management_link() -> None:
    assert (
        build_management_link("https://mawid.example/", "abc") == "https://mawid.example/manage/abc"
    )
