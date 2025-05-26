from asyncio import Future
from pathlib import Path
from typing import cast

import cv2
from detectron2.structures import Instances

from server.algorithms.data_types import BoundingBox, CV_Image, Mask
from server.algorithms.enums import PlayerClasses, Team
from server.algorithms.player_tracker import PlayerTracker
from server.algorithms.services.player_predictor_service import PlayerPredictorService
from server.algorithms.services.player_tracking_service import PlayerTrackingService
from server.data_storage.dto import DatasetDTO, VideoDTO, SubsetDataInputDTO
from server.data_storage.exceptions import NotFoundError
from server.data_storage.protocols import Repository
from server.utils import buffered_generator, chain_video_slices
from server.utils.file_lock import FileLock
from server.views.exceptions.mask_not_found import MaskNotFoundError


class DatasetView:
    """
    Предоставляет интерфейс работы наборами данных разделения на команды.
    """

    def __init__(self, repository: Repository):
        self.repository: Repository = repository

    async def create_dataset_for_video(self, video_id: int) -> DatasetDTO:
        """
        Создает набор данных разделения на команды для видео.

        :param video_id: Идентификатор видео.
        :return: Представление набора данных.
        :raise DataIntegrityError: Если данные нарушают целостность БД.
        """
        async with self.repository.transaction as tr:
            dataset: DatasetDTO = await self.repository.dataset_repo.create_dataset_for_video(
                video_id
            )
            await tr.commit()

        return dataset

    async def get_team_dataset_by_id(self, dataset_id: int) -> DatasetDTO:
        """
        Получает набор данных разделения команд по идентификатору.

        :param dataset_id: Идентификатор набора данных.
        :return: Набор данных.
        :raise ValueError: Неправильный входной идентификатор.
        :raise NotFoundError: Набор данных не существует.
        """
        async with self.repository.transaction:
            return await self.repository.dataset_repo.get_team_dataset_by_id(dataset_id)

    async def create_subset_to_dataset(
        self,
        dataset_id: int,
        from_frame: int,
        to_frame: int,
        frame_buffer_size: int,
        static_directory: Path,
        file_lock: FileLock,
        player_predictor: PlayerPredictorService
    ) -> int:
        """
        Создает новый поднабор данных в наборе данных.

        :param dataset_id: Идентификатор родительского набора данных.
        :param from_frame: С какого кадра производится получения информации.
        :param to_frame: По какой кадр производится получение информации.
        :param frame_buffer_size: Количество кадров в буфере.
        :param static_directory: Папка со статическими файлами.
        :param file_lock: Блокировщик доступа к файлам.
        :param player_predictor: Объект сервиса поиска игроков на поле.
        :return: Идентификатор нового поднабора данных.
        :raise FileNotFound: Если файл с откорректированным искажением не найден.
        :raise ValueError: Неправильные входные данные идентификаторов
        или длинна кадров не совпадает с данными.
        :raise NotFoundError: Видео с привязанным идентификатором не найдено или не найден набор данных.
        :raise IndexError: Неправильные ограничения начального и конечного кадра.
        :raise DataIntegrityError: Нарушение целостности данных (повторяющиеся идентификаторы).
        :raise TimeoutError: Файл уже в обработке и не может быть обработан.
        """
        assert frame_buffer_size >= 1, "Not enough frame buffer size"

        async with self.repository.transaction:
            dataset_info: DatasetDTO = await self.repository.dataset_repo.get_dataset_information_by_id(
                dataset_id
            )
            video_info: VideoDTO | None = await self.repository.video_repo.get_video(
                dataset_info.video_id
            )
            has_crossover: bool = await self.repository.dataset_repo.check_frames_crossover_other_subset(
                dataset_id, from_frame, to_frame
            )

        if video_info is None:
            raise NotFoundError("Video not found")

        if video_info.converted_video_path is None:
            raise FileNotFoundError(
                "Video was not converted with correction, thus not available"
            )

        if has_crossover:
            raise IndexError("Already has crossover with some other dataset")

        video_path: Path = static_directory / "videos" / video_info.converted_video_path
        field_mask_path: Path = video_path.parent / "field_mask.jpeg"

        if not video_path.is_file():
            raise FileNotFoundError(
                "Video file was deleted from disk"
            )

        if not field_mask_path.is_file():
            raise MaskNotFoundError(
                "Field mask not found error"
            )

        async with file_lock.lock_file(field_mask_path):
            mask: Mask = Mask(
                mask=cast(CV_Image, cv2.imread(str(field_mask_path)))
            )

        field_bounding_box: BoundingBox = BoundingBox(
            *mask.get_corners_of_mask()
        )
        player_tracker: PlayerTrackingService = PlayerTrackingService(
            PlayerTracker(),
            mask,
            field_bounding_box
        )

        subset_data: list[list[SubsetDataInputDTO]] = []
        capture = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)

        async with file_lock.lock_file(video_path, timeout=1):
            async for frame_n, frame in buffered_generator(
                chain_video_slices(capture, [(from_frame, to_frame)]),
                frame_buffer_size
            ):
                result_instances: Future[
                    list[Instances]
                ] = await player_predictor.add_inference_task_to_queue(frame)
                resulting_players_instances: Instances = (await result_instances)[0].to("cpu")
                subset_data.append(
                    player_tracker.process_frame(frame_n, resulting_players_instances)
                )

        async with self.repository.transaction as tr:
            subset_id: int = await self.repository.dataset_repo.add_subset_to_dataset(
                dataset_id, from_frame, to_frame, subset_data
            )
            await tr.commit()

        return subset_id

    async def set_player_team(self, subset_id: int, tracking_id: int, team: Team) -> bool:
        """
        Установить команду игрока по номеру отслеживания.

        :param subset_id: Номер поднабора данных.
        :param tracking_id: Номер отслеживания.
        :param team: Команда для назначения.
        :return: Была ли установлена команда.
        :raise NotFoundError: Не найдены записи с таким игроком.
        """
        async with self.repository.transaction as tr:
            has_changed: bool = await self.repository.dataset_repo.set_player_team(
                subset_id, tracking_id, team
            )
            await tr.commit()

        return has_changed

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
        async with self.repository.transaction as tr:
            has_changed: bool = await self.repository.dataset_repo.set_player_class(
                subset_id, tracking_id, player_class
            )
            await tr.commit()

        return has_changed

    async def kill_tracking(self, subset_id: int, tracking_id: int, frame_id: int) -> int:
        """
        Удаляет отслеживание начиная с определенного кадра.

        :param subset_id: Номер поднабора данных.
        :param tracking_id: Номер отслеживания.
        :param frame_id: Номер кадра.
        :return: Сколько точек отслеживания было удалено.
        :raise NotFoundError: Не найдены записи с таким игроком.
        """
        async with self.repository.transaction as tr:
            removed_records: int = await self.repository.dataset_repo.kill_tracking(
                subset_id, tracking_id, frame_id
            )
            await tr.commit()

        return removed_records

    async def get_teams_dataset_size(self, dataset_id: int) -> dict[Team, int]:
        """
        Получает информацию о количестве точек данных с игроками по командам.

        :param dataset_id: Идентификатор набора данных.
        :return: Словарь с командами и количеством точек об игроках в каждой из них.
        :raises NotFoundError: Если набор данных не найден.
        """

        async with self.repository.transaction:
            return await self.repository.dataset_repo.get_teams_dataset_size(dataset_id)
