import pytest
from apps.accounts.infrastructure.models import Role, User


@pytest.mark.django_db
def test_user_manager_normalizes_email() -> None:
    user = User.objects.create_user(email="  Owner@Example.COM ", password="password-123")

    assert user.email == "owner@example.com"
    assert user.check_password("password-123")


@pytest.mark.django_db
def test_superuser_is_owner_and_staff() -> None:
    user = User.objects.create_superuser(email="admin@example.com", password="password-123")

    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.role == Role.OWNER
