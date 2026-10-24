from types import TracebackType

from django.db import transaction

from apps.core.domain.unit_of_work import UnitOfWork


class DjangoUnitOfWork:
    def __init__(self) -> None:
        self._atomic: transaction.Atomic | None = None

    def __enter__(self) -> "DjangoUnitOfWork":
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        assert self._atomic is not None
        self._atomic.__exit__(exc_type, exc_value, traceback)
        self._atomic = None
        return None

    def rollback(self) -> None:
        transaction.set_rollback(True)


def build_unit_of_work() -> UnitOfWork:
    return DjangoUnitOfWork()
