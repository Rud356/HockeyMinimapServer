from sqlalchemy.ext.asyncio import AsyncEngine

from .dataset_repo_sqla import DatasetRepoSQLA
from .frames_repo_sqla import FramesRepoSQLA
from .map_data_repo_sqla import MapDataRepoSQLA
from .player_data_repo_sqla import PlayerDataRepoSQLA
from .project_repo_sqla import ProjectRepoSQLA
from .tables.base import Base
from .transaction_manager_sqla import TransactionManagerSQLA
from .user_repo_sqla import UserRepoSQLA
from .video_repo_sqla import VideoRepoSQLA
from ..protocols import Repository


class RepositorySQLA(Repository):
    def __init__(self, transaction: TransactionManagerSQLA):
        self.transaction: TransactionManagerSQLA = transaction

    @property
    def player_data_repo(self) -> PlayerDataRepoSQLA:
        return PlayerDataRepoSQLA(self.transaction)

    @property
    def dataset_repo(self) -> DatasetRepoSQLA:
        return DatasetRepoSQLA(self.transaction)

    @property
    def frames_repo(self) -> FramesRepoSQLA:
        return FramesRepoSQLA(self.transaction)

    @property
    def user_repo(self) -> UserRepoSQLA:
        return UserRepoSQLA(self.transaction)

    @property
    def video_repo(self) -> VideoRepoSQLA:
        return VideoRepoSQLA(self.transaction)

    @property
    def map_data_repo(self) -> MapDataRepoSQLA:
        return MapDataRepoSQLA(self.transaction)

    @property
    def project_repo(self) -> ProjectRepoSQLA:
        return ProjectRepoSQLA(self.transaction)

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
