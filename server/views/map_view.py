import asyncio
from asyncio import AbstractEventLoop, Future
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from typing import NewType, Optional

from detectron2.structures import Instances

from server.algorithms.data_types import BoundingBox, CV_Image, Mask, Point, RelativePoint
from server.algorithms.data_types.field_extracted_data import FieldExtractedData
from server.algorithms.enums import CameraPosition
from server.algorithms.key_point_placer import KeyPointPlacer
from server.algorithms.services.base.field_data_extraction_protocol import FieldDataExtractionProtocol
from server.algorithms.services.field_data_extraction_service import FieldDataExtractionService
from server.algorithms.services.field_predictor_service import FieldPredictorService
from server.algorithms.video_processing import VideoProcessing
from server.data_storage.dto import MinimapDataDTO
from server.data_storage.dto.relative_point_dto import RelativePointDTO
from server.data_storage.exceptions import NotFoundError
from server.data_storage.protocols import Repository
from server.utils.config import MinimapKeyPointConfig
from server.utils.config.key_point import KeyPoint

RelativeMinimapKeyPointConfig = NewType("RelativeMinimapKeyPointConfig", MinimapKeyPointConfig)


class MapView:
    """
    Предоставляет интерфейс получения данных о мини-карте и управления ими.
    """
    def __init__(self, repository: Repository):
        self.repository: Repository = repository

    async def create_point_mapping_for_video(
        self, video_id: int, mapping: dict[RelativePointDTO, RelativePointDTO]
    ) -> int:
        """
        Добавляет соотношения точек карты и игрового поля.

        :param video_id: Идентификатор видео.
        :param mapping: Соотношения точек.
        :return: Количество добавленных точек.
        :raise DataIntegrityError: Нарушена целостность данных, возможно видео не существует.
        """
        async with self.repository.transaction as tr:
            count: int = await self.repository.map_data_repo.create_point_mapping_for_video(
                video_id, mapping
            )
            await tr.commit()

        return count

    async def get_points_mapping_for_video(self, video_id: int) -> list[MinimapDataDTO]:
        """
        Получает все точки соотнесения для видео.

        :param video_id: Идентификатор видео.
        :return: Список точек соотнесения с видео.
        """
        async with self.repository.transaction:
            return await self.repository.map_data_repo.get_points_mapping_for_video(video_id)

    async def drop_all_mapping_points_for_video(self, video_id: int) -> int:
        """
        Удаляет все соотнесенные точки, относящиеся к видео.

        :param video_id: Идентификатор видео.
        :return: Количество удаленных точек.
        :raise NotFoundError: Точки не найдены.
        """
        async with self.repository.transaction as tr:
            count: int = await self.repository.map_data_repo.drop_all_mapping_points_for_video(
                video_id
            )
            await tr.commit()

        if count == 0:
            raise NotFoundError("Points not found for specified video")

        return count

    async def edit_point_from_mapping(
        self,
        map_data_id: int,
        point_on_camera: Optional[RelativePointDTO] = None,
        point_on_minimap: Optional[RelativePointDTO] = None,
        is_used: Optional[bool] = None
    ) -> bool:
        """
        Изменяет конкретное соотношение точек карты с точкой из видео.

        :param map_data_id: Идентификатор соотнесения точек к карте.
        :param point_on_camera: Данные точки на камере.
        :param point_on_minimap: Данные точки на мини-карте.
        :param is_used: Используется ли точка.
        :return: Были ли изменения сохранены.
        :raise NotFoundError: Точка не найдена.
        :raise DataIntegrityError: Переданные данные не верные.
        """
        async with self.repository.transaction as tr:
            modified: bool = await self.repository.map_data_repo.edit_point_from_mapping(
                map_data_id,
                point_on_camera,
                point_on_minimap,
                is_used
            )
            await tr.commit()

        return modified

    async def get_key_points_from_video(
        self,
        video_path: Path,
        camera_position: CameraPosition,
        map_config: MinimapKeyPointConfig,
        video_processing: VideoProcessing,
        field_predictor_service: FieldPredictorService,
        timestamp: Optional[float] = None,
        anchor_point: Optional[RelativePointDTO] = None
    ) -> tuple[dict[RelativePointDTO, RelativePointDTO], Mask]:
        """
        Получает из кадра видео по временной метке разметку поля и соотношение точек
        к точкам камеры.

        :param video_path: Путь до видео файла.
        :param camera_position: Положение камеры относительно поля.
        :param map_config: Конфигурация ключевых точек поля.
        :param video_processing: Обработчик видео.
        :param field_predictor_service: Сервис нейросети для выделения ключевых точек.
        :param timestamp: Временная метка.
        :param anchor_point: Опциональная ключевая точка центра.
        :return: Соотнесение ключевых точек поля к точкам с камеры и маска поля.
        """
        # Get map to be in relative coordinates
        relative_map_config: RelativeMinimapKeyPointConfig = self.get_relative_minimap_points(
            map_config
        )
        frame: CV_Image = await self.extract_field_frame(video_path, video_processing, timestamp)

        width: int
        height: int
        height, width, _ = frame.shape
        frame_resolution: tuple[int, int] = (width, height)

        # Create key point placer that will work with relative map coordinates
        key_points_placer: KeyPointPlacer = KeyPointPlacer(
            relative_map_config,
            camera_position,
            frame_resolution
        )
        # Create field data extractor that will get data about key points in frame
        field_data_extractor: FieldDataExtractionService = FieldDataExtractionService(
            key_points_placer
        )

        absolute_anchor_point: Point | None = None
        if anchor_point is not None:
            absolute_anchor_point = Point.from_relative_coordinates(
                RelativePoint(x=anchor_point.x, y=anchor_point.y),
                frame_resolution
            )

        # Get field data where map points and field points are relative
        field_data: FieldExtractedData = await self.compute_key_points_of_field_from_frame(
            frame, field_data_extractor, field_predictor_service, absolute_anchor_point
        )

        field_points_mapping: dict[RelativePointDTO, RelativePointDTO] = {
            RelativePointDTO(x=key_point.x, y=key_point.y):
                RelativePointDTO(x=video_point.x, y=video_point.y)
            for key_point, video_point in field_data.key_points.items()
        }
        return field_points_mapping, field_data.map_mask

    @staticmethod
    async def compute_key_points_of_field_from_frame(
        frame: CV_Image,
        field_data_extractor: FieldDataExtractionProtocol,
        field_predictor_service: FieldPredictorService,
        anchor_point: Optional[Point] = None
    ) -> FieldExtractedData:
        """
        Рассчитывает положение точек

        :param frame: Кадр видео.
        :param field_data_extractor: Сервис получения ключевых точек и их расположения по полю.
        :param field_predictor_service: Нейросеть предсказания объекта поля.
        :param anchor_point: Ключевая точка центра.
        :return: Объект с данными о поле.
        """
        fut: Future[list[Instances]] = await field_predictor_service.add_inference_task_to_queue(
            frame
        )
        results: list[Instances] = await fut

        field_elements: Instances = results[0].to("cpu")
        return field_data_extractor.get_field_data(
            field_elements, anchor_point
        )

    @staticmethod
    async def extract_field_frame(
        source_path: Path,
        video_processing: VideoProcessing,
        timestamp: Optional[float] = None,
    ) -> CV_Image:
        """
        Получает отдельный кадр из видео.

        :param source_path: Путь до видео файла.
        :param video_processing: Обработчик видео.
        :param timestamp: Временная метка кадра.
        :return: Изображение с кадра.
        """
        loop: AbstractEventLoop = asyncio.get_running_loop()
        result_frame: CV_Image

        with ThreadPoolExecutor(1) as executor:
            result_frame, _ = await loop.run_in_executor(
                executor,
                video_processing.render_frame_sample,
                source_path,
                timestamp
            )

        return result_frame

    @staticmethod
    def get_relative_minimap_points(map_config: MinimapKeyPointConfig) -> RelativeMinimapKeyPointConfig:
        """
        Преобразует координаты мини-карты в относительные координаты мини-карты.

        :param map_config: Исходная конфигурация мини-карты.
        :return: Конфигурация мини-карты с относительными точками.
        """
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

        relative_key_points = {
            # Those are boundaries of map
            "top_left_field_point": map_config.top_left_field_point,
            "bottom_right_field_point": map_config.bottom_right_field_point
        }

        for key, value in map_config.model_dump().items():
            if key not in {"top_left_field_point", "bottom_right_field_point"}:
                relative_point = Point(
                    value["x"],
                    value["y"]
                ).to_relative_coordinates_inside_bbox(map_bbox)

                relative_key_points[key] = KeyPoint(
                    x=relative_point.x,
                    y=relative_point.y
                )

        return RelativeMinimapKeyPointConfig(
            MinimapKeyPointConfig(**relative_key_points)
        )
