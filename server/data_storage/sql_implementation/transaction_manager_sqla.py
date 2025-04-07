from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from ..protocols.transaction_manager import TransactionManager


class TransactionManagerSQLA(TransactionManager):
    """
    Управляет транзакциями ORM SQLAlchemy.
    """

    def __init__(self, session: AsyncSession, transaction: AsyncSessionTransaction):
        self.session: AsyncSession = session
        self.transaction: AsyncSessionTransaction = transaction

    async def start_nested_transaction(self) -> "TransactionManager":
        return TransactionManagerSQLA(
            self.session,
            self.transaction.session.begin_nested()
        )

    async def commit(self) -> None:
        await self.transaction.commit()

    async def rollback(self) -> None:
        await self.transaction.rollback()
