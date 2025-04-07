from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from ..protocols.transaction_manager import TransactionManager


class TransactionManagerSQLA(TransactionManager):
    """
    Управляет транзакциями ORM SQLAlchemy.
    """

    def __init__(self, session: AsyncSession, transaction: AsyncSessionTransaction):
        self.session: AsyncSession = session
        self.transaction: AsyncSessionTransaction = transaction

    async def start_nested_transaction(self) -> "TransactionManagerSQLA":
        return TransactionManagerSQLA(
            self.session,
            self.session.begin_nested()
        )

    async def commit(self) -> None:
        await self.transaction.commit()

    async def rollback(self) -> None:
        await self.transaction.rollback()

    async def __aenter__(self) -> Self:
        """
        Начинает транзакцию.

        :return: Объект, управляющий транзакцией.
        """
        await self.transaction.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        """
        Вызывает закрытие транзакции.

        :param exc_type: Тип исключения.
        :param exc_value: Необработанные исключения.
        :param traceback: Объект трейсбека.
        :return: Ничего.
        """
        await self.transaction.__aexit__(exc_type, exc_value, traceback)
        return None
