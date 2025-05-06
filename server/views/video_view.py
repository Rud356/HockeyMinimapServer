import asyncio
import uuid
from concurrent.futures import Executor
from pathlib import Path
from typing import Any, Optional

import cv2

from server.algorithms.data_types import CV_Image
from server.algorithms.disk_space_allocator import DiskSpaceAllocator
from server.algorithms.enums import CameraPosition
from server.algorithms.video_processing import VideoProcessing
from server.data_storage.dto import VideoDTO
from server.data_storage.exceptions import NotFoundError
from server.data_storage.protocols import Repository
from server.utils.providers import StaticDirSpaceAllocator, TmpDirSpaceAllocator


class VideoView:
    """
    Предоставляет интерфейс работы с видео и данными о них.
    """

    def __init__(self, repository: Repository):
        self.repository: Repository = repository

    async def create_new_video_from_upload(
        self,
        source_path: Path,
        video_directory: Path,
        video_processing_worker: Executor,
        video_processing: VideoProcessing,
        storage_allocator: DiskSpaceAllocator
    ) -> VideoDTO:
        """
        Создает новое видео в БД на основе входного файла и конвертирует его в формат
        для работы в браузере.

        :param video_processing: Обработчик видео.
        :param source_path: Путь до исходного загруженного файла.
        :param video_directory: Выходная директория.
        :param video_processing_worker: Объект потока для запуска обработки видео.
        :param storage_allocator: Объект выделения места для хранения видео на диске в конечной папке.
        :return: Объект, представляющий данные о видео.
        """
        video_processing.probe_video(source_path)
        assert video_directory.is_dir(), "Video directory in config must be a directory"
        current_loop = asyncio.get_running_loop()

        # Create new directory for string video
        video_dest_dir = video_directory / str(uuid.uuid1())
        video_dest_dir.mkdir()

        video_path: Path = video_dest_dir / "source_video.mp4"
        async with storage_allocator.preallocate_disk_space(source_path.stat().st_size):
            # Converting video
            video_info: dict[str, Any] = await current_loop.run_in_executor(
                video_processing_worker,
                video_processing.compress_video,
                source_path,
                video_path
            )

        # Make db record
        async with self.repository.transaction as tr:
            video_dto: VideoDTO = await self.repository.video_repo.create_new_video(
                video_processing.get_fps_from_probe(video_info),
                video_path.relative_to(video_directory).as_posix(),
            )
            await tr.commit()

        return video_dto

    async def get_video(self, video_id: int) -> VideoDTO:
        """
        Получает видео по идентификатору.

        :param video_id: Идентификатор видео.
        :return: Ничего или данные о видео.
        :raise NotFoundError: Если видео не найдено в БД.
        """
        async with self.repository.transaction:
            video: VideoDTO | None = await self.repository.video_repo.get_video(video_id)

        if video is None:
            raise NotFoundError("Video was not found")

        return video

    async def get_videos(self, limit: int = 100, offset: int = 0) -> list[VideoDTO]:
        """
        Выводит список информации о видео в системе.

        :param limit: Количество записей.
        :param offset: Отступ от первой записи.
        :return: Список информации о видео.
        """

        async with self.repository.transaction:
            return await self.repository.video_repo.get_videos(limit, offset)

    async def adjust_corrective_coefficients(
        self, video_id: int, k1: float, k2: float,
        override_coefficients_after_convertion: bool = False
    ) -> None:
        """
        Изменяет коэффициенты коррекции видео.

        :param video_id: Идентификатор видео.
        :param k1: Первичный коэффициент коррекции.
        :param k2: Вторичный коэффициент коррекции.
        :param override_coefficients_after_convertion: Перезаписать коэффициенты конвертации.
        :raise NotFoundError: Если видео не найдено в БД.
        :raise DataIntegrityError: Если коэффициенты были неверно заданы.
        :raise ValueError: Если видео уже было обработано с текущими параметрами.
        :return: Ничего.
        """
        async with self.repository.transaction as tr:
            video: VideoDTO | None = await self.repository.video_repo.get_video(video_id)
            if video is None:
                raise NotFoundError("Video was not found")

            if video.is_converted and not override_coefficients_after_convertion:
                raise ValueError("Video already was converted with current parameters")

            if override_coefficients_after_convertion:
                await self.repository.video_repo.set_flag_video_is_converted(video_id, False)

            await self.repository.video_repo.adjust_corrective_coefficients(video_id, k1, k2)
            await tr.commit()

    async def generate_correction_preview(
        self,
        video_id: int,
        executor: Executor,
        video_processing: VideoProcessing,
        static_directory: Path,
        dest: Path,
        frame_timestamp: Optional[float] = None
    ) -> None:
        """
        Подготавливает пример кадра с примененной коррекцией.

        :param video_id: Идентификатор видео.
        :param executor: Объект запуска обработки.
        :param video_processing: Обработчик видео.
        :param static_directory: Путь до директории с видео.
        :param dest: Путь для сохранения примера кадра.
        :param frame_timestamp: Временная метка для примера.
        :return: Ничего.
        :raise NotFoundError: Если видео не найдено в БД.
        :raise FileNotFound: Файл не найден на диске.
        :raise ValueError: Временная метка вне длительности видео.
        :raise KeyError: Временная метка конца не найдена в метаданных.
        :raise InvalidFileFormat: Неподдерживаемый формат файла предоставлен в качестве файла.
        """
        loop = asyncio.get_running_loop()

        async with self.repository.transaction:
            video: VideoDTO | None = await self.repository.video_repo.get_video(video_id)

            if video is None:
                raise NotFoundError("Video was not found")

        image: CV_Image
        image, _ = await loop.run_in_executor(
            executor,
            video_processing.render_correction_sample,
            static_directory / "videos" / video.source_video_path,
            video.corrective_coefficient_k1,
            video.corrective_coefficient_k2,
            frame_timestamp
        )

        await loop.run_in_executor(
            executor,
            cv2.imwrite,
            str(dest.resolve()),
            image,
            []
        )

    async def apply_video_correction(
        self,
        video_id: int,
        executor: Executor,
        video_processing: VideoProcessing,
        static_directory: Path,
        render_again: bool,
        temp_disk_space_allocator: TmpDirSpaceAllocator,
        dest_disk_space_allocator: StaticDirSpaceAllocator,
    ) -> None:
        """
        Применяет коррекцию ко всему видео.

        :param video_id: Идентификатор видео.
        :param executor: Исполнитель синхронных задач.
        :param video_processing: Объект обработки видео.
        :param static_directory: Директория со статическими файлами.
        :param render_again: Нужно ли корректировать видео заново, если файл уже был откорректирован.
        :param temp_disk_space_allocator: Аллокатор места во временной папке.
        :param dest_disk_space_allocator: Аллокатор места в конечной папке.
        :return: Ничего.
        """
        loop = asyncio.get_running_loop()

        async with self.repository.transaction:
            video: VideoDTO | None = await self.repository.video_repo.get_video(video_id)

            if video is None:
                raise NotFoundError("Video was not found")

        if video.is_converted and not render_again:
            raise ValueError("Video is already corrected")

        video_dir: Path = static_directory / "videos"
        source_video: Path = video_dir / video.source_video_path
        dest_file: Path = source_video.parent / "corrected_video.mp4"

        if video.corrective_coefficient_k1 == 0 and video.corrective_coefficient_k2 == 0:
            async with self.repository.transaction as tr:
                await self.repository.video_repo.set_flag_video_is_converted(
                    video_id,
                    True,
                    video_dir,
                    source_video
                )
                await tr.commit()
                return

        async with (
            temp_disk_space_allocator.preallocate_disk_space(source_video.stat().st_size),
            dest_disk_space_allocator.preallocate_disk_space(source_video.stat().st_size)
        ):
            await loop.run_in_executor(
                executor,
                video_processing.render_corrected_video,
                source_video,
                dest_file,
                video.corrective_coefficient_k1,
                video.corrective_coefficient_k2
            )

        async with self.repository.transaction as tr:
            await self.repository.video_repo.set_flag_video_is_converted(
                video_id,
                True,
                video_dir,
                dest_file
            )
            await tr.commit()

    async def change_camera_position_for_video(
        self,
        video_id: int,
        camera_position: CameraPosition
    ) -> bool:
        """
        Изменяет положение камеры относительно поля для видео.

        :param video_id: Идентификатор видео.
        :param camera_position: Положение камеры.
        :return: Применены ли изменения.
        :raise NotFoundError: Если видео не найдено в БД.
        :raise ValueError: Если передано неверное значение.
        """

        async with self.repository.transaction as tr:
            changed = await self.repository.video_repo.set_camera_position(
                video_id,
                camera_position
            )
            await tr.commit()

        return changed
