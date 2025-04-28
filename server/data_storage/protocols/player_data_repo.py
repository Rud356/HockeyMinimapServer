from typing import Protocol, runtime_checkable

from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.enums.team import Team
from server.data_storage.dto.frame_data_dto import FrameDataDTO
from server.data_storage.dto.player_alias import PlayerAlias
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
        players_data_on_frame: list[list[PlayerDataDTO]]
    ) -> None:
        """
        Создает информацию об игроках на кадре в базе данных.

        :param video_id: Видео к которому принадлежит кадр.
        :param players_data_on_frame: Информация об игроках на каждом кадре.
        :return: Ничего.
        :raises NotFoundError: Если кадр для вставки не найден.
        :raises DataIntegrityError: Если вставлены неправильные данные.
        """

    async def kill_tracking(self, video_id: int, frame_id: int, tracking_id: int) -> int:
        """
        Удаляет данные об отслеживании игроков.

        :param video_id: Идентификатор видео.
        :param frame_id: Номер кадра в видео, с которого прекращается отслеживание.
        :param tracking_id: Номер отслеживания.
        :return: Количество удаленных записей.
        :raises NotFoundError: Если не найдено записей.
        """

    async def kill_all_tracking_of_player(self, video_id: int, tracking_id: int) -> int:
        """
        Удаляет все данные о конкретном отслеживании.

        :param video_id: Идентификатор видео.
        :param tracking_id: Номер отслеживания.
        :return: Количество удаленных записей.
        :raises NotFoundError: Если не найдено записей.
        """

    async def set_player_identity_to_user_id(self, video_id: int, tracking_id: int, player_id: int) -> int:
        """
        Устанавливает отслеживанию пользовательский идентификатор.

        :param video_id: Идентификатор видео.
        :param tracking_id: Идентификатор отслеживания.
        :param player_id: Внутренний идентификатор пользовательского назначения.
        :return: Количество изменённых записей.
        """

    async def set_team_to_tracking_id(self, video_id: int, frame_id: int, tracking_id: int, team: Team) -> None:
        """
        Устанавливает команду для отслеживания игрока, если не было назначений до этого.

        :param video_id: Идентификатор видео.
        :param frame_id: Номер кадра в видео, на котором игроку назначена команда.
        :param tracking_id: Номер отслеживания.
        :param team: Команда для назначения.
        :return: Ничего.
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
        :raises NotFoundError: Если не найдено записей.
        """

    async def get_user_alias_for_players(self, video_id: int) -> dict[int, PlayerAlias]:
        """
        Получает все пользовательские идентификаторы игроков, привязанные к видео.

        :param video_id: Идентификатор видео.
        :return: Соотнесение идентификаторов пользовательских назначений к именам этих назначений.
        """

    async def create_user_alias_for_players(
        self,
        video_id: int,
        users_player_alias: str,
        player_team: Team | None = None
    ) -> int:
        """
        Создает пользовательский идентификатор для игроков в видео.

        :param video_id: Идентификатор видео.
        :param users_player_alias: Пользовательское имя для игрока.
        :param player_team: Команда игрока.
        :return: Внутренний идентификатор соотнесения.
        :raise DataIntegrityError: Неправильные входные данные или видео не существует.
        """

    async def delete_player_alias(self, custom_player_id: int) -> bool:
        """
        Удаляет пользовательский идентификатор пользователя.

        :param custom_player_id: Идентификатор пользовательского имени игрока.
        :return: Было ли удалено имя игрока.
        :raise NotFoundError: Имя игрока с представленным идентификатором не найдено.
        """

    async def rename_player_alias(self, custom_player_id: int, users_player_alias: str) -> None:
        """
        Изменяет название идентификатора игрока.

        :param custom_player_id: Идентификатор пользовательского имени игрока.
        :param users_player_alias: Пользовательское имя для игрока.
        :return: Ничего.
        :raise NotFoundError: Имя игрока с представленным идентификатором не найдено.
        :raise DataIntegrityError: Неправильные входные данные или видео не существует.
        """

    async def change_player_alias_team(self, custom_player_id: int, users_player_team: Team) -> None:
        """
        Изменяет название идентификатора игрока.

        :param custom_player_id: Идентификатор пользовательского имени игрока.
        :param users_player_team: Пользовательское назначение команды для игрока.
        :return: Ничего.
        :raise NotFoundError: Имя игрока с представленным идентификатором не найдено.
        :raise DataIntegrityError: Неправильные входные данные или видео не существует.
        """

    async def get_tracking_from_frames(self, video_id: int, limit: int = 120, offset: int = 0) -> FrameDataDTO:
        """
        Получает все отслеживания игроков начиная с кадра по n кадр.

        :param video_id: Идентификатор видео.
        :param limit: Количество кадров для получения.
        :param offset: С какого кадра начинать получение.
        :return: Данные о кадрах.
        :raise IndexError: Кадры в пределах не существуют.
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
        :raises NotFoundError: Видео не найдено или не найдены кадры видео.
        """

    async def get_frames_min_and_max_ids_with_limit_offset(
        self, video_id: int, limit: int, offset: int
    ) -> tuple[int, int]:
        """
        Получает идентификаторы минимального и максимального кадра с отступом и лимитом.

        :param video_id: Идентификатор видео.
        :param limit: Сколько кадров взять.
        :param offset: Сколько кадров отступить от начала выборки.
        :return: Минимальный и максимальный номер кадра в видео.
        :raise IndexError: Кадры в пределах не существуют.
        """
