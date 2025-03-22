from typing import Protocol, runtime_checkable


@runtime_checkable
class TransactionManager(Protocol):
    """
    Управляет транзакциями и сохранением изменений.
    """

    async def commit(self) -> None:
        """
        Сохраняет изменения, сделанные во время транзакции.

        :return: Ничего.
        """

    async def rollback(self) -> None:
        """
        Отменяет изменения, сделанные во время транзакции.

        :return: Ничего.
        """
