from typing import Protocol, runtime_checkable

from server.data_storage.dto.project_dto import ProjectDTO
from server.data_storage.dto.project_export_dto import ProjectExportDTO
from server.data_storage.protocols.dataset_repo import DatasetRepo
from server.data_storage.protocols.frames_repo import FramesRepo
from server.data_storage.protocols.map_data_repo import MapDataRepo
from server.data_storage.protocols.player_data_repo import PlayerDataRepo
from server.data_storage.protocols.project_repo import ProjectRepo
from server.data_storage.protocols.transaction_manager import TransactionManager
from server.data_storage.protocols.user_repo import UserRepo
from server.data_storage.protocols.video_repo import VideoRepo


@runtime_checkable
class Repository(Protocol):
    transaction: TransactionManager

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
    def user_repo(self) -> UserRepo:
        ...

    @property
    def video_repo(self) -> VideoRepo:
        ...

    @property
    def map_data_repo(self) -> MapDataRepo:
        ...

    @property
    def project_repo(self) -> ProjectRepo:
        ...

    async def export_project_data(self, project_id: int) -> ProjectExportDTO:
        """
        Экспортирует данные о проекте.

        :param project_id: Идентификатор проекта для экспорта.
        :return: Данные о всем проекте.
        """
        ...

    async def import_project_data(self, project_data: ProjectExportDTO) -> ProjectDTO:
        """
        Импортирует сохраненные данные.

        :param project_data: Данные проекта для импорта.
        :return: Данные о новом проекте.
        """
        ...
