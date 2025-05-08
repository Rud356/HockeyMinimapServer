from asyncio import Future
from pathlib import Path

import cv2
from detectron2.structures import Instances

from server.algorithms.services.player_predictor_service import PlayerPredictorService
from server.algorithms.services.player_tracking_service import PlayerTrackingService
from server.data_storage.dto import DatasetDTO, VideoDTO
from server.data_storage.dto.subset_data_input import SubsetDataInputDTO
from server.data_storage.exceptions import NotFoundError
from server.data_storage.protocols import Repository
from server.utils import buffered_generator, chain_video_slices


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
        return await self.repository.dataset_repo.get_team_dataset_by_id(dataset_id)

    async def create_subset_to_dataset(
        self,
        dataset_id: int,
        from_frame: int,
        to_frame: int,
        frame_buffer_size: int,
        static_directory: Path,
        player_tracker: PlayerTrackingService,
        player_predictor: PlayerPredictorService
    ) -> int:
        """
        Создает новый поднабор данных в наборе данных.

        :param dataset_id: Идентификатор родительского набора данных.
        :param from_frame: С какого кадра производится получения информации.
        :param to_frame: По какой кадр производится получение информации.
        :param frame_buffer_size: Количество кадров в буфере.
        :param static_directory: Папка со статическими файлами.
        :param player_tracker: Объект сервиса отслеживания игроков.
        :param player_predictor: Объект сервиса поиска игроков на поле.
        :return: Идентификатор нового поднабора данных.
        :raise FileNotFound: Если файл с откорректированным искажением не найден.
        :raise ValueError: Неправильные входные данные идентификаторов
        или длинна кадров не совпадает с данными.
        :raise NotFoundError: Видео с привязанным идентификатором не найдено или не найден набор данных.
        :raise IndexError: Неправильные ограничения начального и конечного кадра.
        :raise DataIntegrityError: Нарушение целостности данных (повторяющиеся идентификаторы).
        """
        assert frame_buffer_size >= 1, "Not enough frame buffer size"

        dataset_info: DatasetDTO = (
            await self.repository.dataset_repo.get_dataset_information_by_id(
                dataset_id
            )
        )
        video_info: VideoDTO | None = await self.repository.video_repo.get_video(
            dataset_info.video_id
        )

        if video_info is None:
            raise NotFoundError("Video not found")

        has_crossover: bool = await self.repository.dataset_repo.check_frames_crossover_other_subset(
            dataset_id, from_frame, to_frame
        )

        if video_info.converted_video_path is None:
            raise FileNotFoundError(
                "Video was not converted with correction, thus not available"
            )

        video_path: Path = static_directory / "videos" / video_info.converted_video_path

        if not video_path.is_file():
            raise FileNotFoundError(
                "Video file was deleted from disk"
            )

        if has_crossover:
            raise IndexError("Already has crossover with some other dataset")

        subset_data: list[list[SubsetDataInputDTO]] = []
        capture = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)

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
