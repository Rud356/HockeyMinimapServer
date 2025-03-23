from typing import Protocol, runtime_checkable

from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.enums.team import Team
from server.data_storage.dto.frame_data_dto import FrameDataDTO
from server.data_storage.dto.player_data_dto import PlayerDataDTO
from server.data_storage.protocols.transaction_manager import TransactionManager


@runtime_checkable
class PlayerDataRepo(Protocol):
    """
    Управляет данными о перемещениях игроков.
    """
    transaction: TransactionManager

    async def insert_player_data(
        self,
        video_id: int,
        frame_id: int,
        players_data_on_frame: list[PlayerDataDTO]
    ) -> None:
        """
        Создает информацию об игроках на кадре в базе данных.

        :param video_id: Видео к которому принадлежит кадр.
        :param frame_id: К какому кадру принадлежит информация.
        :param players_data_on_frame: Информация о кадре.
        :return: Ничего.
        """

    async def kill_tracking(self, video_id: int, frame_id: int, tracking_id: int) -> int:
        """
        Удаляет данные об отслеживании игроков.

        :param video_id: Идентификатор видео.
        :param frame_id: Номер кадра в видео, с которого прекращается отслеживание.
        :param tracking_id: Номер отслеживания.
        :return: Количество удаленных записей.
        """

    async def kill_all_tracking_of_player(self, video_id: int, tracking_id: int) -> int:
        """
        Удаляет все данные о конкретном отслеживании.

        :param video_id: Идентификатор видео.
        :param tracking_id: Номер отслеживания.
        :return: Количество удаленных записей.
        """

    async def set_player_identity_to_user_id(self, video_id: int, tracking_id: int, player_id: int) -> int:
        """
        Устанавливает отслеживанию пользовательский идентификатор.

        :param video_id: Идентификатор видео.
        :param tracking_id: Идентификатор отслеживания.
        :param player_id: Внутренний идентификатор пользовательского назначения.
        :return: Количество изменённых записей.
        """

    async def set_team_to_tracking_id(self, video_id: int, frame_id: int, tracking_id: int, team: Team) -> int:
        """
        Устанавливает команду для отслеживания игрока, если не было назначений до этого.

        :param video_id: Идентификатор видео.
        :param frame_id: Номер кадра в видео, на котором игроку назначена команда.
        :param tracking_id: Номер отслеживания.
        :param team: Команда для назначения.
        :return: Количество измененных записей.
        """

    async def set_player_class_to_tracking_id(
        self, video_id: int, frame_id: int, tracking_id: int, class_id: PlayerClasses
    ) -> int:
        """
        Устанавливает класс игрока для отслеживания, если не было назначений до этого.

        :param video_id: Идентификатор видео.
        :param frame_id: Номер кадра в видео, на котором игроку назначена команда.
        :param tracking_id: Номер отслеживания.
        :param class_id: Идентификатор класса игрока.
        :return: Количество измененных записей.
        """

    async def get_user_ids_for_players(self, video_id: int) -> dict[int, str]:
        """
        Получает все пользовательские идентификаторы игроков, привязанные к видео.

        :param video_id: Идентификатор видео.
        :return: Соотнесение идентификаторов пользовательских назначений к именам этих назначений.
        """

    async def create_user_id_for_players(self, video_id: int, users_player_alias: str) -> int:
        """
        Создает пользовательский идентификатор для игроков в видео.

        :param video_id: Идентификатор видео.
        :param users_player_alias: Пользовательское имя для игрока.
        :return: Внутренний идентификатор соотнесения.
        """

    async def get_tracking_from_frames(self, video_id: int, limit: int = 120, offset: int = 0) -> FrameDataDTO:
        """
        Получает все отслеживания игроков начиная с кадра по n кадр.

        :param video_id: Идентификатор видео.
        :param limit: Количество кадров для получения.
        :param offset: С какого кадра начинать получение.
        :return: Данные о кадрах.
        """

    async def get_all_tracking_data(self, video_id: int) -> FrameDataDTO:
        """
        Получает информацию об игроках со всех кадров в видео.

        :param video_id: Идентификатор видео.
        :return: Информация о всех кадрах в видео.
        """

    async def get_frames_min_and_max_ids_in_video(self, video_id: int) -> tuple[int, int]:
        """
        Идентификатор первого и последнего кадра видео.

        :param video_id: Идентификатор видео.
        :return: Минимальный и максимальный номер кадра в видео.
        """
