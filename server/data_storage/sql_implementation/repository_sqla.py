from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from .transaction_manager_sqla import TransactionManagerSQLA
from ..protocols import Repository
from .tables.base import Base


class RepositorySQLA(Repository):
    def __init__(self, session: AsyncSession, transaction: Optional[TransactionManagerSQLA] = None):
        if transaction is not None:
            self.transaction: TransactionManagerSQLA = transaction

        elif (transaction_init := session.get_transaction()) is not None:
            self.transaction = TransactionManagerSQLA(session, transaction_init)

        else:
            self.transaction = TransactionManagerSQLA(session, session.begin())

    @staticmethod
    async def init_db(engine: AsyncEngine) -> None:
        """
        Инициализирует БД.

        :type engine: Подключение к базе данных.
        :return: Ничего.
        """
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @staticmethod
    async def drop_db(engine: AsyncEngine) -> None:
        """
        Удаляет все данные из БД.

        :type engine: Подключение к базе данных.
        :return: Ничего.
        """
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
