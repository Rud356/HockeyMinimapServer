from typing import AsyncIterator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from server.data_storage.protocols import Repository, TransactionManager
from server.data_storage.sql_implementation.repository_sqla import RepositorySQLA
from server.data_storage.sql_implementation.transaction_manager_sqla import TransactionManagerSQLA


class SQLAlchemyProvider(Provider):
    def __init__(self, engine: AsyncEngine):
        super().__init__()
        self.engine: AsyncEngine = engine
        self.session_maker: async_sessionmaker[
            AsyncSession
        ] = async_sessionmaker(
            self.engine,
            expire_on_commit=False
        )

    @provide(scope=Scope.REQUEST)
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        """
        Получает сессию SQLAlchemy.

        :return: Сессия SQLAlchemy.
        """
        session: AsyncSession = self.session_maker()
        yield session
        await session.close()
        return

    @provide(scope=Scope.REQUEST)
    def get_transaction_manager(self, session: AsyncSession) -> TransactionManagerSQLA:
        """
        Получает менеджер транзакций.

        :param session: Асинхронная сессия SQLAlchemy.
        :return: Менеджер транзакции.
        """

        if (transaction_init := session.get_transaction()) is not None:
            return TransactionManagerSQLA(session, transaction_init)

        return TransactionManagerSQLA(session, session.begin())

    @provide(scope=Scope.REQUEST)
    def get_transaction_manager_protocol(self, session: AsyncSession) -> TransactionManager:
        return self.get_transaction_manager(session)

    @provide(scope=Scope.REQUEST)
    def get_repository(self, transaction: TransactionManagerSQLA) -> Repository:
        """
        Получает репозиторий SQLAlchemy.

        :return: SQLAlchemy версия репозитория.
        """
        return RepositorySQLA(transaction)
