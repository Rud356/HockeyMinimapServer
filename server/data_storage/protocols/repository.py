from pathlib import Path
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
    """
    Обеспечивает доступ и управление данными из БД.
    """
    transaction: TransactionManager

    @property
    def player_data_repo(self) -> PlayerDataRepo:
        """
        Объект для взаимодействия с хранилищем данных игроков.

        :return: Объект репозитория игроков.
        """

    @property
    def dataset_repo(self) -> DatasetRepo:
        """
        Объект для взаимодействия с хранилищем наборов данных разделения команд.

        :return: Объект взаимодействия с набором данных о командах.
        """

    @property
    def frames_repo(self) -> FramesRepo:
        """
        Объект взаимодействия с хранилищем кадров видео.

        :return: Объект репозитория кадров.
        """

    @property
    def user_repo(self) -> UserRepo:
        """
        Объект взаимодействия с хранилищем пользователей.

        :return: Объект репозитория пользователей.
        """

    @property
    def video_repo(self) -> VideoRepo:
        """
        Объект взаимодействия с хранилищем видео.

        :return: Объект репозитория видео.
        """

    @property
    def map_data_repo(self) -> MapDataRepo:
        """
        Объект взаимодействия с хранилищем данных о карте.

        :return: Объект репозитория карты.
        """

    @property
    def project_repo(self) -> ProjectRepo:
        """
        Объект взаимодействия с хранилищем проектов.

        :return: Объект репозитория проектов.
        """

    async def export_project_data(self, project_id: int) -> ProjectExportDTO:
        """
        Экспортирует данные о проекте.

        :param project_id: Идентификатор проекта для экспорта.
        :return: Данные о всем проекте.
        :raise NotFoundError: Не найдено валидного проекта с таким идентификатором.
        :raise ValueError: Неправильные входные данные.
        :raise InvalidProjectState: Проект не обработан для вывода в файл.
        """

    async def import_project_data(
        self,
        static_path: Path,
        new_video_folder: Path,
        project_data: ProjectExportDTO
    ) -> ProjectDTO:
        """
        Импортирует сохраненные данные.

        :param static_path: Путь до статической директории.
        :param new_video_folder: Новая папка с видео.
        :param project_data: Данные проекта для импорта.
        :return: Данные о новом проекте.
        :raise ValidationError: Предоставленные данные не соответствуют формату.
        :raise ValueError: Пути до видео пустые.
        :raise DataIntegrityError: Не удалось сохранить целостность объектов.
        """
