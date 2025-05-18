import asyncio
from asyncio import AbstractEventLoop, Future, Task
from concurrent.futures import Executor
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import AsyncGenerator, cast

import cv2
from detectron2.structures import Instances
from torch.utils.data import Subset
from torchvision.datasets import ImageFolder, VisionDataset

from server.algorithms.data_types import BoundingBox, CV_Image, Mask, PlayerData, Point
from server.algorithms.enums import PlayerClasses, Team
from server.algorithms.nn import (
    TeamDetectionPredictor,
    TeamDetectorModel,
    TeamDetectorTeacher,
    device,
    team_detector_transform,
)
from server.algorithms.player_tracker import PlayerTracker
from server.algorithms.players_mapper import PlayersMapper
from server.algorithms.services.map_video_renderer_service import MapVideoRendererService
from server.algorithms.services.player_data_extraction_service import PlayerDataExtractionService
from server.algorithms.services.player_predictor_service import PlayerPredictorService
from server.algorithms.services.player_tracking_service import PlayerTrackingService
from server.data_storage.dto import BoxDTO, DatasetDTO, FrameDataDTO, MinimapDataDTO, SubsetDataDTO, VideoDTO
from server.data_storage.dto.player_alias import PlayerAlias
from server.data_storage.dto.player_data_dto import PlayerDataDTO
from server.data_storage.dto.relative_point_dto import RelativePointDTO
from server.data_storage.exceptions import NotFoundError
from server.data_storage.protocols import Repository
from server.utils import async_video_reader, buffered_generator, chain_video_slices
from server.utils.config import MinimapKeyPointConfig, VideoPreprocessingConfig
from server.utils.dataset_utils import split_dataset
from server.utils.file_lock import FileLock
from server.utils.providers import RenderBuffer, RenderWorker
from server.views.exceptions import InvalidProjectState, MaskNotFoundError, NotEnoughPlayersUniformExamples


class PlayerDataView:
    """
    Предоставляет интерфейс получения данных об игроках и управления ими.
    """
    def __init__(self, repository: Repository):
        self.repository: Repository = repository

    async def generate_tracking_data(
        self,
        video_id: int,
        frame_buffer_size: int,
        file_lock: FileLock,
        static_directory: Path,
        player_predictor: PlayerPredictorService
    ) -> None:
        """
        Генерирует данные о перемещениях игроков.

        :param video_id: Идентификатор видео.
        :param frame_buffer_size: Объем буфера кадров для чтения.
        :param file_lock: Блокировщик доступа к файлам.
        :param static_directory: Путь до статической директории.
        :param player_predictor: Сервис определения игроков.
        :return: Ничего.
        :raise FileNotFound: Видеофайл не найден на диске.
        :raise MaskNotFoundError: Не найдена маска для видео.
        :raise NotFoundError: Видео не найдено.
        :raise InvalidProjectState: Нет данных для проведения обработки.
        :raise NotEnoughPlayersUniformExamples: Нет достаточного количества примеров формы игроков.
        :raise DataIntegrityError: Если уже имеются добавленные данные.
        :raise TimeoutError: Файл уже обрабатывается.
        """
        async with self.repository.transaction:
            video_info: VideoDTO | None = await self.repository.video_repo.get_video(
                video_id
            )
            map_data: list[MinimapDataDTO] = await self.repository.map_data_repo.get_points_mapping_for_video(
                video_id
            )

            if len(map_data) < 4:
                raise InvalidProjectState("Not enough map points")

            if video_info is None:
                raise NotFoundError("Video was not found")

            if video_info.dataset_id is None:
                raise InvalidProjectState("Project does not have dataset")

            if video_info.converted_video_path is None:
                raise InvalidProjectState("Project must have converted video for this stage")

            if video_info.is_processed:
                raise InvalidProjectState("Project was already processed")

            dataset_sizes: dict[Team, int] = await self.repository.dataset_repo.get_teams_dataset_size(
                video_info.dataset_id
            )

            if any((class_size < 50 for class_size in dataset_sizes.values())):
                raise NotEnoughPlayersUniformExamples(
                    "Not enough of examples for uniform",
                    dataset_sizes
                )

            dataset_info: DatasetDTO = await self.repository.dataset_repo.get_dataset_information_by_id(
                video_info.dataset_id
            )

        video_file: Path = static_directory / "videos" / video_info.converted_video_path
        mask_file: Path = video_file.parent / "field_mask.jpeg"

        if not video_file.is_file():
            raise FileNotFoundError("Video file was deleted from disk")

        # 2 second to get a hold of map,
        # or else it is assumed that video is processing already
        async with file_lock.lock_file(mask_file, timeout=2):
            if not mask_file.is_file():
                raise MaskNotFoundError("Field mask was not found")

            mask: CV_Image = cast(
                CV_Image,
                cv2.imread(
                    str(mask_file.resolve())
                )
            )

        # 1 second to get a hold of video,
        # or else it is assumed that video is processing already
        async with file_lock.lock_file(video_file, timeout=1):
            frame_slices: list[tuple[int, int]] = []
            players_on_frames: dict[int, list[SubsetDataDTO]] = {}

            for subset in dataset_info.subsets:
                frame_slices.append(
                    (subset.from_frame_id, subset.to_frame_id)
                )

                for player_data in subset.subset_data:
                    players_on_frames.setdefault(
                        player_data.frame_id, []
                    ).append(player_data)

            with TemporaryDirectory(prefix="hmms_dataset_") as tmp:
                train_subset, validate_subset = await self._prepare_dataset_for_team_detection(
                    video_file,
                    Path(tmp),
                    frame_buffer_size,
                    frame_slices, players_on_frames
                )
                model: TeamDetectorModel = await self._prepare_team_detector(
                    train_subset, validate_subset
                )

            # Prepare methods
            team_predictor: TeamDetectionPredictor = TeamDetectionPredictor(
                model, team_detector_transform, device
            )
            mapper: PlayersMapper = PlayersMapper(
                # Inside a relative bounding box
                BoundingBox(Point(0, 0), Point(1, 1)),
                {
                    mapping.point_on_minimap: mapping.point_on_camera
                        for mapping in map_data
                }
            )
            field_mask: Mask = Mask(mask=mask)
            player_data_extractor: PlayerDataExtractionService = PlayerDataExtractionService(
                team_predictor,
                mapper,
                PlayerTracker(),
                field_mask,
                BoundingBox(*field_mask.get_corners_of_mask())
            )

            capture = cv2.VideoCapture(str(video_file), cv2.CAP_FFMPEG)
            player_data_on_frames: list[list[PlayerDataDTO]] = []

            # Process video
            async for frame_n, frame in buffered_generator(
                async_video_reader(capture),
                frame_buffer_size
            ):
                fut: Future[list[Instances]] = await player_predictor.add_inference_task_to_queue(frame)
                player_instances: Instances = (await fut)[0].to('cpu')
                player_inferred_data: list[PlayerData] = player_data_extractor.process_frame(
                    frame, player_instances
                )

                frame_data: list[PlayerDataDTO] = []
                for player in player_inferred_data:
                    player_info: PlayerDataDTO = PlayerDataDTO(
                        tracking_id=player.tracking_id,
                        player_id=None,
                        player_name=None,
                        team_id=player.team_id,
                        class_id=player.class_id,
                        player_on_camera=BoxDTO(
                            top_point=RelativePointDTO(
                                x=player.bounding_box_on_camera.min_point.x,
                                y=player.bounding_box_on_camera.min_point.y
                            ),
                            bottom_point=RelativePointDTO(
                                x=player.bounding_box_on_camera.max_point.x,
                                y=player.bounding_box_on_camera.max_point.y
                            )
                        ),
                        player_on_minimap=RelativePointDTO(
                            x=player.position.x,
                            y=player.position.y
                        )
                    )
                    frame_data.append(player_info)

                player_data_on_frames.append(frame_data)

            # Add records
            await self.repository.player_data_repo.insert_player_data(
                video_info.video_id,
                player_data_on_frames
            )

    async def kill_tracking(self, video_id: int, frame_id: int, tracking_id: int) -> int:
        """
        Удаляет данные об отслеживании игроков.

        :param video_id: Идентификатор видео.
        :param frame_id: Номер кадра в видео, с которого прекращается отслеживание.
        :param tracking_id: Номер отслеживания.
        :return: Количество удаленных записей.
        :raises NotFoundError: Если не найдено записей.
        """
        async with self.repository.transaction as tr:
            result: int = await self.repository.player_data_repo.kill_tracking(
                video_id, frame_id, tracking_id
            )
            await tr.commit()

        return result

    async def kill_all_tracking_of_player(self, video_id: int, tracking_id: int) -> int:
        """
        Удаляет все данные о конкретном отслеживании.

        :param video_id: Идентификатор видео.
        :param tracking_id: Номер отслеживания.
        :return: Количество удаленных записей.
        :raises NotFoundError: Если не найдено записей.
        """
        async with self.repository.transaction as tr:
            result: int = await self.repository.player_data_repo.kill_all_tracking_of_player(
                video_id, tracking_id
            )
            await tr.commit()

        return result

    async def set_player_identity_to_user_id(
        self, video_id: int, tracking_id: int, player_id: int
    ) -> int:
        """
        Устанавливает отслеживанию пользовательский идентификатор.

        :param video_id: Идентификатор видео.
        :param tracking_id: Идентификатор отслеживания.
        :param player_id: Внутренний идентификатор пользовательского назначения.
        :return: Количество изменённых записей.
        """
        async with self.repository.transaction as tr:
            result: int = await self.repository.player_data_repo.set_player_identity_to_user_id(
                video_id, tracking_id, player_id
            )
            await tr.commit()

        return result

    async def set_team_to_tracking_id(
        self, video_id: int, frame_id: int, tracking_id: int, team: Team
    ) -> None:
        """
        Устанавливает команду для отслеживания игрока, если не было назначений до этого.

        :param video_id: Идентификатор видео.
        :param frame_id: Номер кадра в видео, на котором игроку назначена команда.
        :param tracking_id: Номер отслеживания.
        :param team: Команда для назначения.
        :return: Ничего.
        """
        async with self.repository.transaction as tr:
            await self.repository.player_data_repo.set_team_to_tracking_id(
                video_id, frame_id, tracking_id, team
            )
            await tr.commit()

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
        async with self.repository.transaction as tr:
            result: int = await self.repository.player_data_repo.set_player_class_to_tracking_id(
                video_id, frame_id, tracking_id, class_id
            )
            await tr.commit()

        return result

    async def get_user_alias_for_players(self, video_id: int) -> dict[int, PlayerAlias]:
        """
        Получает все пользовательские идентификаторы игроков, привязанные к видео.

        :param video_id: Идентификатор видео.
        :return: Соотнесение идентификаторов пользовательских назначений к именам этих назначений.
        """
        async with self.repository.transaction:
            return await self.repository.player_data_repo.get_user_alias_for_players(video_id)

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
        async with self.repository.transaction as tr:
            result: int = await self.repository.player_data_repo.create_user_alias_for_players(
                video_id, users_player_alias, player_team
            )
            await tr.commit()

        return result

    async def delete_player_alias(self, custom_player_id: int) -> bool:
        """
        Удаляет пользовательский идентификатор пользователя.

        :param custom_player_id: Идентификатор пользовательского имени игрока.
        :return: Было ли удалено имя игрока.
        :raise NotFoundError: Имя игрока с представленным идентификатором не найдено.
        """
        async with self.repository.transaction as tr:
            result: bool = await self.repository.player_data_repo.delete_player_alias(
                custom_player_id
            )
            await tr.commit()

        return result

    async def rename_player_alias(
        self, custom_player_id: int, users_player_alias: str
    ) -> None:
        """
        Изменяет название идентификатора игрока.

        :param custom_player_id: Идентификатор пользовательского имени игрока.
        :param users_player_alias: Пользовательское имя для игрока.
        :return: Ничего.
        :raise NotFoundError: Имя игрока с представленным идентификатором не найдено.
        :raise DataIntegrityError: Неправильные входные данные или видео не существует.
        """
        async with self.repository.transaction as tr:
            await self.repository.player_data_repo.rename_player_alias(
                custom_player_id, users_player_alias
            )
            await tr.commit()

    async def change_player_alias_team(
        self, custom_player_id: int, users_player_team: Team
    ) -> None:
        """
        Изменяет название идентификатора игрока.

        :param custom_player_id: Идентификатор пользовательского имени игрока.
        :param users_player_team: Пользовательское назначение команды для игрока.
        :return: Ничего.
        :raise NotFoundError: Имя игрока с представленным идентификатором не найдено.
        :raise DataIntegrityError: Неправильные входные данные или видео не существует.
        """
        async with self.repository.transaction as tr:
            await self.repository.player_data_repo.change_player_alias_team(
                custom_player_id, users_player_team
            )
            await tr.commit()

    async def get_tracking_from_frames(
        self, video_id: int, limit: int = 120, offset: int = 0
    ) -> FrameDataDTO:
        """
        Получает все отслеживания игроков начиная с кадра по n кадр.

        :param video_id: Идентификатор видео.
        :param limit: Количество кадров для получения.
        :param offset: С какого кадра начинать получение.
        :return: Данные о кадрах.
        :raise IndexError: Кадры в пределах не существуют.
        """
        async with self.repository.transaction:
            return await self.repository.player_data_repo.get_tracking_from_frames(
                video_id, limit, offset
            )

    async def get_all_tracking_data(self, video_id: int) -> FrameDataDTO:
        """
        Получает информацию об игроках со всех кадров в видео.

        :param video_id: Идентификатор видео.
        :return: Информация о всех кадрах в видео.
        """
        async with self.repository.transaction:
            return await self.repository.player_data_repo.get_all_tracking_data(
                video_id
            )

    async def generate_map_video(
        self,
        video_id: int,
        file_lock: FileLock,
        map_config: MinimapKeyPointConfig,
        map_buffer: RenderBuffer,
        map_renderer: RenderWorker,
        video_processing_config: VideoPreprocessingConfig,
        static_directory: Path
    ) -> Path:
        """
        Отрисовывает видео мини-карты.

        :param video_id: Идентификатор видео.
        :param file_lock: Блокировщик доступа к файлам.
        :param map_config: Конфигурация мини-карты.
        :param map_buffer: Объем буфера кадров для вывода карты.
        :param map_renderer: Обработчик отрисовки кадров.
        :param video_processing_config: Настройки вывода видео.
        :param static_directory: Путь до статической папки ресурсов.
        :return: Путь до нового файла с мини-картой.
        """
        loop: AbstractEventLoop = asyncio.get_running_loop()

        async with self.repository.transaction:
            video_info: VideoDTO | None = await self.repository.video_repo.get_video(
                video_id
            )
            map_data: list[MinimapDataDTO] = await self.repository.map_data_repo.get_points_mapping_for_video(
                video_id
            )

            if len(map_data) < 4:
                raise InvalidProjectState("Not enough map points")

            if video_info is None:
                raise NotFoundError("Video was not found")

            if video_info.dataset_id is None:
                raise InvalidProjectState("Project does not have dataset")

            if video_info.converted_video_path is None:
                raise InvalidProjectState("Project must have converted video for this stage")

            if not video_info.is_processed:
                raise InvalidProjectState("Project was not processed before")

        video_file: Path = static_directory / "videos" / video_info.converted_video_path
        map_file: Path = static_directory / "map.png"
        map_video: Path = video_file.parent / 'output_map.mp4'

        if not video_file.is_file():
            raise FileNotFoundError("Video file was deleted from disk")

        if not map_file.is_file():
            raise FileNotFoundError("Map file was not found")

        map_image: CV_Image = cast(
            CV_Image,
            cv2.imread(
                str(map_file.resolve())
            )
        )
        map_bbox: BoundingBox = BoundingBox(
            Point(
                map_config.top_left_field_point.x,
                map_config.top_left_field_point.y
            ),
            Point(
                map_config.bottom_right_field_point.x,
                map_config.bottom_right_field_point.y
            )
        )
        video_render_service: MapVideoRendererService = MapVideoRendererService(
            map_renderer,
            video_info.fps,
            map_video,
            map_bbox,
            map_image,
            frame_buffer_limit=map_buffer,
            video_processing_config=video_processing_config
        )
        renderer_task: Task = loop.create_task(video_render_service.run())

        data_renderer: AsyncGenerator[
            int,
            list[PlayerDataDTO] | None
        ] = video_render_service.data_renderer()
        await data_renderer.asend(None)

        async with self.repository.transaction:
            frame_data: FrameDataDTO = await self.repository.player_data_repo.get_all_tracking_data(video_id)

        async with file_lock.lock_file(map_video, timeout=1):
            for frame in frame_data.frames:
                await data_renderer.asend(frame)

            try:
                await data_renderer.asend(None)

            except StopAsyncIteration:
                pass

            await renderer_task

        return map_video

    async def get_frames_min_and_max_ids_in_video(self, video_id: int) -> tuple[int, int]:
        """
        Идентификатор первого и последнего кадра видео.

        :param video_id: Идентификатор видео.
        :return: Минимальный и максимальный номер кадра в видео.
        :raises NotFoundError: Видео не найдено или не найдены кадры видео.
        """
        async with self.repository.transaction:
            return await self.repository.player_data_repo.get_frames_min_and_max_ids_in_video(
                video_id
            )

    async def _prepare_dataset_for_team_detection(
        self,
        video_path: Path,
        dest_directory: Path,
        frame_buffer_size: int,
        frame_slices: list[tuple[int, int]],
        players_on_frames: dict[int, list[SubsetDataDTO]],
    ) -> tuple[Subset, Subset]:
        """
        Создает набор данных о разделении игроков на команды.

        :param video_path: Путь до видео.
        :param dest_directory: Путь набора данных.
        :param frame_buffer_size: Объем буфера кадров.
        :param frame_slices: Срезы кадров с наборами данных.
        :param players_on_frames: Информация об игроках на кадрах.
        :return: Обучающая и проверочная подвыборка из набора данных.
        """
        loop: AbstractEventLoop = asyncio.get_running_loop()
        capture = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)

        home_team_dir: Path = dest_directory / "Team_home"
        away_team_dir: Path = dest_directory / "Team_away"
        home_team_dir.mkdir(exist_ok=True)
        away_team_dir.mkdir(exist_ok=True)

        home_team_counter: int = 0
        away_team_counter: int = 0

        with ThreadPoolExecutor(1) as executor:
            async for frame_n, frame in buffered_generator(
                chain_video_slices(capture, frame_slices),
                frame_buffer_size
            ):
                players: list[tuple[Team, CV_Image]] = PlayerTrackingService.get_players_data_from_frame(
                    frame,
                    players_on_frames[frame_n]
                )

                for player_team, player_image in players:
                    if player_team == Team.Home:
                        home_team_counter += 1
                        await self._write_image(
                            player_image,
                            home_team_dir / f"Home_{home_team_counter}.png",
                            loop, executor
                        )

                    else:
                        away_team_counter += 1
                        await self._write_image(
                            player_image,
                            away_team_dir / f"Away_{home_team_counter}.png",
                            loop, executor
                        )

        dataset: VisionDataset = ImageFolder(
            dest_directory,
            transform=team_detector_transform
        )
        return split_dataset(dataset)

    @staticmethod
    async def _prepare_team_detector(
        train_subset: Subset, val_subset: Subset
    ) -> TeamDetectorModel:
        """
        Обучает нейросеть разделению игроков на команды.

        :param train_subset: Обучающая выборка.
        :param val_subset: Проверочная выборка.
        :return: Обученная модель.
        """
        trainer: TeamDetectorTeacher = TeamDetectorTeacher(
            train_subset,
            val_subset,
            100,
            TeamDetectorModel(),
            device
        )
        loop: AbstractEventLoop = asyncio.get_running_loop()

        with ThreadPoolExecutor(1) as executor:
            model: TeamDetectorModel = await loop.run_in_executor(
                executor, trainer.train_nn
            )

        return model

    @staticmethod
    async def _write_image(
        image: CV_Image,
        dest: Path,
        loop: AbstractEventLoop,
        executor: Executor
    ) -> None:
        """
        Сохраняет изображение на диск.

        :param image: Объект изображения.
        :param dest: Путь до файла.
        :param loop: Используемый цикл программы.
        :param executor: Исполнитель задачи.
        :return: Ничего.
        """
        await loop.run_in_executor(
            executor,
            cv2.imwrite,
            str(dest.resolve()),
            image,
            []
        )
