from sqlalchemy.ext.asyncio import AsyncEngine

from .tables.base import Base
from .transaction_manager_sqla import TransactionManagerSQLA
from .user_repo_sqla import UserRepoSQLA
from ..protocols import DatasetRepo, MapDataRepo, PlayerDataRepo, ProjectRepo, Repository, UserRepo, VideoRepo
from ..protocols.frames_repo import FramesRepo


class RepositorySQLA(Repository):
    def __init__(self, transaction: TransactionManagerSQLA):
        self.transaction: TransactionManagerSQLA = transaction

    @property
    def player_data_repo(self) -> PlayerDataRepo:
        ...

    @property
    def dataset_repo(self) -> DatasetRepo:
        ...

    @property
    def frames_repo(self) -> FramesRepo:
        ...

    @property
    def user_repo(self) -> UserRepoSQLA:
        return UserRepoSQLA(
            self.transaction
        )

    @property
    def video_repo(self) -> VideoRepo:
        ...

    @property
    def map_data_repo(self) -> MapDataRepo:
        ...

    @property
    def project_repo(self) -> ProjectRepo:
        ...

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
