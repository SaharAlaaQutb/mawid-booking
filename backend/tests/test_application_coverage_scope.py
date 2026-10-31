from apps.accounts.application.scope import resolve_actor
from apps.accounts.infrastructure.models import Role, User


def test_resolve_actor_returns_scope_for_active_staff(staff):
    user = User.objects.create_user(
        email="actor@example.com",
        password="test-password",
        role=Role.OWNER,
    )
    staff.user = user
    staff.is_active = True
    staff.save(update_fields=["user", "is_active"])
    scope = resolve_actor(user)
    assert scope.user_id == user.id
    assert scope.role == Role.OWNER.value
    assert scope.staff.id == staff.id
