from contextlib import AbstractAsyncContextManager
from typing import Protocol, Self, runtime_checkable


@runtime_checkable
class TransactionManager(Protocol, AbstractAsyncContextManager):
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

    async def start_nested_transaction(self) -> "TransactionManager":
        """
        Создает вложенную транзакцию.

        :return: Новый менеджер вложенной транзакции.
        """
        ...

    async def __aenter__(self) -> Self:
        """
        Начинает транзакцию.

        :return: Объект, управляющий транзакцией.
        """
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """
        Вызывает закрытие транзакции.

        :param exc_type: Тип исключения.
        :param exc_value: Необработанные исключения.
        :param traceback: Объект трейсбека.
        :return: Ничего.
        """
        return None
