from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from server.data_storage.protocols import Repository
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
    def get_session(self) -> AsyncSession:
        """
        Получает сессию SQLAlchemy.

        :return: Сессия SQLAlchemy.
        """
        return self.session_maker()

    @provide(scope=Scope.REQUEST)
    def get_transaction_manager(self, session: AsyncSession) -> TransactionManagerSQLA:
        """
        Получает менеджер транзакций.

        :param session: Асинхронная сессия SQLAlchemy.
        :return: Менеджер транзакции.
        """

        if (transaction_init := session.get_transaction()) is not None:
            return TransactionManagerSQLA(session, transaction_init)

        else:
            return TransactionManagerSQLA(session, session.begin())

    @provide(scope=Scope.REQUEST)
    def get_repository(self) -> Repository:
        """
        Получает репозиторий SQLAlchemy.

        :return: SQLAlchemy версия репозитория.
        """
        return RepositorySQLA(
            self.get_transaction_manager(
                self.get_session()
            )
        )
