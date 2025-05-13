from typing import Protocol, runtime_checkable

from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.enums.team import Team
from server.data_storage.dto.dataset_dto import DatasetDTO
from server.data_storage.dto.subset_data_input import SubsetDataInputDTO
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
        :raise DataIntegrityError: Если данные нарушают целостность БД.
        """

    async def get_dataset_information_by_id(self, dataset_id: int) -> DatasetDTO:
        """
        Возвращает только информацию, прямо находящуюся в наборе данных.

        :param dataset_id: Идентификатор набора данных.
        :return: Данные о наборе, без информации из поднаборов.
        :raise ValueError: Неправильный входной идентификатор.
        :raise NotFoundError: Набор данных не существует.
        """

    async def get_team_dataset_by_id(self, dataset_id: int) -> DatasetDTO:
        """
        Получает набор данных разделения команд по идентификатору.

        :param dataset_id: Идентификатор набора данных.
        :return: Набор данных.
        :raise ValueError: Неправильный входной идентификатор.
        :raise NotFoundError: Набор данных не существует.
        """

    async def add_subset_to_dataset(
        self,
        dataset_id: int,
        from_frame: int,
        to_frame: int,
        subset_data: list[list[SubsetDataInputDTO]]
    ) -> int:
        """
        Создает поднабор данных в рамках одного набора данных.

        :param dataset_id: Идентификатор набора данных.
        :param from_frame: С какого кадра начинается набор данных.
        :param to_frame: Каким кадром заканчивается набор данных.
        :param subset_data: Список, где каждый элемент представляет
        данные об игроках на каждом кадре.
        :return: Идентификатор поднабора данных.
        :raise ValueError: Несоответствие начальных и конечных кадров
        или длинны массива с количеством кадров.
        :raise NotFoundError: Набор данных не существует.
        :raise DataIntegrityError: Если данные нарушают целостность БД.
        """

    async def set_player_team(self, subset_id: int, tracking_id: int, team: Team) -> bool:
        """
        Установить команду игрока по номеру отслеживания.

        :param subset_id: Номер поднабора данных.
        :param tracking_id: Номер отслеживания.
        :param team: Команда для назначения.
        :return: Была ли установлена команда.
        :raise NotFoundError: Не найдены записи с таким игроком.
        """

    async def set_player_class(
        self, subset_id: int, tracking_id: int, player_class: PlayerClasses
    ) -> bool:
        """
        Изменяет класс игрока по номеру отслеживания.

        :param subset_id: Номер поднабора данных.
        :param tracking_id: Номер отслеживания.
        :param player_class: Класс игрока.
        :return: Был ли успешно изменен класс.
        :raise NotFoundError: Не найдены записи с таким игроком.
        """

    async def kill_tracking(self, subset_id: int, tracking_id: int, frame_id: int) -> int:
        """
        Удаляет отслеживание начиная с определенного кадра.

        :param subset_id: Номер поднабора данных.
        :param tracking_id: Номер отслеживания.
        :param frame_id: Номер кадра.
        :return: Сколько точек отслеживания было удалено.
        :raise NotFoundError: Не найдены записи с таким игроком.
        """

    async def get_teams_dataset_size(self, dataset_id: int) -> dict[Team, int]:
        """
        Получает информацию о количестве точек данных с игроками по командам.

        :param dataset_id: Идентификатор набора данных.
        :return: Словарь с командами и количеством точек об игроках в каждой из них.
        :raises NotFoundError: Если не найден набор данных.
        """

    async def check_frames_crossover_other_subset(
        self, dataset_id: int, from_frame: int, to_frame: int
    ) -> bool:
        """
        Проверяет, пересекаются ли данные с кадра по кадр с каким-либо
         другим поднабором данных.

        :param dataset_id: Идентификатор набора данных.
        :param from_frame: С какого кадра проверка.
        :param to_frame: По какой кадр проверка.
        :return: Есть ли пересечение кадров с другими наборами.
        :raise IndexError: Когда предоставлены неправильные данные ограничений.
        """