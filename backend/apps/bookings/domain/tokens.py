import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

MANAGEMENT_TOKEN_TTL_DAYS = 7


@dataclass(frozen=True, slots=True)
class IssuedManagementToken:
    value: str
    token_hash: str
    expires_at: datetime


def hash_management_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def issue_management_token(starts_at: datetime) -> IssuedManagementToken:
    if starts_at.tzinfo is None:
        raise ValueError("starts_at must be timezone-aware")
    value = secrets.token_urlsafe(32)
    return IssuedManagementToken(
        value=value,
        token_hash=hash_management_token(value),
        expires_at=starts_at + timedelta(days=MANAGEMENT_TOKEN_TTL_DAYS),
    )


def build_management_link(base_url: str, token: str) -> str:
    return f"{base_url.rstrip('/')}/manage/{token}"
