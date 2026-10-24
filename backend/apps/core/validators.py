from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.core.domain.timezones import is_valid_timezone


def validate_timezone(value: str) -> None:
    if not is_valid_timezone(value):
        raise ValidationError(_("%(value)s is not a valid IANA timezone."), params={"value": value})
