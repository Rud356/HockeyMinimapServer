from pathlib import Path
from typing import Optional, cast

from pydantic import ValidationError
from sqlalchemy import Select
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncScalarResult

from server.algorithms.enums import CameraPosition
from server.data_storage.dto import VideoDTO
from server.data_storage.exceptions import DataIntegrityError, NotFoundError
from server.data_storage.protocols import VideoRepo
from server.data_storage.sql_implementation.tables import Video
from server.data_storage.sql_implementation.transaction_manager_sqla import TransactionManagerSQLA


class VideoRepoSQLA(VideoRepo):
    transaction: TransactionManagerSQLA

    def __init__(self, transaction: TransactionManagerSQLA):
        self.transaction: TransactionManagerSQLA = transaction

    async def create_new_video(
        self,
        fps: float,
        source_video_path: Path
    ) -> VideoDTO:
        try:
            video_record = Video(
                source_video_path=str(source_video_path),
                fps=fps
            )
            async with await self.transaction.start_nested_transaction() as tr:
                tr.session.add(video_record)
                await tr.commit()

            return VideoDTO(
                video_id=video_record.video_id,
                fps=video_record.fps,
                corrective_coefficient_k1=video_record.corrective_coefficient_k1,
                corrective_coefficient_k2=video_record.corrective_coefficient_k2,
                camera_position=video_record.camera_position,
                is_converted=video_record.is_converted,
                is_processed=video_record.is_processed,
                source_video_path=Path(video_record.source_video_path),
                converted_video_path=cast(Path, video_record.converted_video_path),
                dataset_id=video_record.dataset_id
            )

        except (IntegrityError, ProgrammingError, AttributeError, ValidationError) as err:
            raise DataIntegrityError("Video creation had database constraints broken or data is invalid") from err

    async def list_all_uploaded_videos_names(self, from_directory: Path) -> list[Path]:
        return [
            p.relative_to(from_directory) for p in map(Path, from_directory.iterdir())
            if p.is_file() and p.name != '.gitkeep'
        ]

    async def get_videos(self, limit: int = 100, offset: int = 0) -> list[VideoDTO]:
        query: Select[tuple[VideoDTO, ...]] = Select(Video).limit(limit).offset(offset).order_by(Video.video_id)
        result: AsyncScalarResult[VideoDTO] = await self.transaction.session.stream_scalars(query)
        videos: list[VideoDTO] = []

        async for video_record in result:
            try:
                videos.append(
                    VideoDTO(
                        video_id=video_record.video_id,
                        fps=video_record.fps,
                        corrective_coefficient_k1=video_record.corrective_coefficient_k1,
                        corrective_coefficient_k2=video_record.corrective_coefficient_k2,
                        camera_position=video_record.camera_position,
                        is_converted=video_record.is_converted,
                        is_processed=video_record.is_processed,
                        source_video_path=Path(video_record.source_video_path),
                        converted_video_path=video_record.converted_video_path,
                        dataset_id=video_record.dataset_id
                    )
                )

            except ValidationError:
                continue

        return videos

    async def get_video(self, video_id: int) -> Optional[VideoDTO]:
        try:
            video_record: Optional[Video] = await self._get_video(video_id)

        except ProgrammingError as err:
            raise ValueError("Invalid input data types") from err

        if video_record is None:
            return None

        try:
            return VideoDTO(
                video_id=video_record.video_id,
                fps=video_record.fps,
                corrective_coefficient_k1=video_record.corrective_coefficient_k1,
                corrective_coefficient_k2=video_record.corrective_coefficient_k2,
                camera_position=video_record.camera_position,
                is_converted=video_record.is_converted,
                is_processed=video_record.is_processed,
                source_video_path=Path(video_record.source_video_path),
                converted_video_path=cast(Path, video_record.converted_video_path),
                dataset_id=video_record.dataset_id
            )

        except ValidationError as err:
            raise ValueError("Invalid data types") from err

    async def set_flag_video_is_converted(
        self, video_id: int, flag_value: bool, from_directory: Path, converted_video_path: Path
    ) -> bool:
        if not (from_directory / converted_video_path).is_file():
            raise ValueError(f"Invalid file path {from_directory / converted_video_path}")

        video_record: Optional[Video] = await self._get_video(video_id)

        if video_record is None:
            raise ValueError("Video does not exists")

        async with await self.transaction.start_nested_transaction() as tr:
            video_record.converted_video_path = str(converted_video_path)
            video_record.is_converted = flag_value

            await tr.commit()

        return flag_value

    async def set_flag_video_is_processed(self, video_id: int, flag_value: bool) -> bool:
        video_record: Optional[Video] = await self._get_video(video_id)

        if video_record is None:
            raise ValueError("Video does not exists")

        async with await self.transaction.start_nested_transaction() as tr:
            video_record.is_processed = flag_value
            await tr.commit()

        return flag_value

    async def adjust_corrective_coefficients(self, video_id: int, k1: float, k2: float) -> None:
        video_record: Optional[Video] = await self._get_video(video_id)

        if video_record is None:
            raise NotFoundError()

        try:
            async with await self.transaction.start_nested_transaction() as tr:
                video_record.corrective_coefficient_k1 = k1
                video_record.corrective_coefficient_k2 = k2

                await tr.commit()

        except (ProgrammingError, IntegrityError) as err:
            raise DataIntegrityError("Invalid coefficients values") from err

    async def set_camera_position(self, video_id: int, camera_position: CameraPosition) -> bool:
        video_record: Optional[Video] = await self._get_video(video_id)

        if video_record is None:
            raise NotFoundError()

        async with await self.transaction.start_nested_transaction() as tr:
            video_record.camera_position = CameraPosition(camera_position)
            await tr.commit()

        return True

    async def _get_video(self, video_id: int) -> Optional[Video]:
        """
        Получает объект записи видео.

        :param video_id: Идентификатор видео.
        :return: Запись в БД о видео или ничего.
        """
        video: Optional[Video] = (await self.transaction.session.execute(
            Select(Video).where(Video.video_id == video_id)
        )).scalar_one_or_none()

        return video