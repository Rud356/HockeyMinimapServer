from typing import Protocol, runtime_checkable

from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.enums.team import Team
from server.data_storage.dto.dataset_dto import DatasetDTO
from server.data_storage.protocols.transaction_manager import TransactionManager


@runtime_checkable
class DatasetRepo(Protocol):
    """
    Управляет данными о дата сетах для обучения нейросети разметки команд.
    """
    transaction: TransactionManager

    async def create_dataset_for_video(self, video_id: int) -> DatasetDTO:
        """
        Создает новый датасет, привязанный к видео.

        :param video_id: Идентификатор видео.
        :return: Данные о наборе данных.
        """

    async def get_team_dataset_by_id(self, dataset_id: int) -> DatasetDTO:
        """
        Получает набор данных выделения команд по идентификатору.

        :param dataset_id: Идентификатор набора данных.
        :return: Набор данных.
        """
        ...

    async def set_player_team(self, subset_id: int, tracking_id: int, team: Team) -> bool:
        """
        Установить команду игрока по номеру отслеживания.

        :param subset_id: Номер поднабора данных.
        :param tracking_id: Номер отслеживания.
        :param team: Команда для назначения.
        :return: Была ли установлена команда.
        """
        ...

    async def change_player_class(self, subset_id: int, tracking_id: int, player_class: PlayerClasses) -> bool:
        """
        Изменяет класс игрока по номеру отслеживания.

        :param subset_id: Номер поднабора данных.
        :param tracking_id: Номер отслеживания.
        :param player_class: Класс игрока.
        :return: Был ли успешно изменен класс.
        """
        ...

    async def kill_tracking(self, subset_id: int, tracking_id: int, frame_id: int) -> int:
        """
        Удаляет отслеживание начиная с определенного кадра.

        :param subset_id: Номер поднабора данных.
        :param tracking_id: Номер отслеживания.
        :param frame_id: Номер кадра.
        :return: Сколько точек отслеживания было удалено.
        """
        ...

    async def get_teams_dataset_size(self, dataset_id: int) -> dict[Team, int]:
        """
        Получает информацию о количестве точек данных с игроками по командам.

        :param dataset_id: Идентификатор набора данных.
        :return: Словарь с командами и количеством точек об игроках в каждой из них.
        """
        ...
