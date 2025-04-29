import asyncio
import uuid
from concurrent.futures import Executor
from pathlib import Path
from typing import Any

from server.algorithms.disk_space_allocator import DiskSpaceAllocator
from server.algorithms.video_processing import VideoProcessing
from server.data_storage.dto import VideoDTO
from server.data_storage.protocols import Repository


class VideoView:
    """
    Предоставляет интерфейс работы с видео и данными о них.
    """

    def __init__(
        self,
        repository: Repository,
        video_processing: VideoProcessing
    ):
        self.repository: Repository = repository
        self.video_processing: VideoProcessing = video_processing

    async def create_new_video_from_upload(
        self,
        source_path: Path,
        video_directory: Path,
        video_processing_worker: Executor,
        storage_allocator: DiskSpaceAllocator
    ) -> VideoDTO:
        """
        Создает новое видео в БД на основе входного файла и конвертирует его в формат
        для работы в браузере.

        :param source_path: Путь до исходного загруженного файла.
        :param video_directory: Выходная директория.
        :param video_processing_worker: Объект потока для запуска обработки видео.
        :param storage_allocator: Объект выделения места для хранения видео на диске в конечной папке.
        :return: Объект, представляющий данные о видео.
        """
        assert video_directory.is_dir(), "Video directory in config must be a directory"
        current_loop = asyncio.get_running_loop()

        # Create new directory for string video
        video_dest_dir = video_directory / str(uuid.uuid1())
        video_dest_dir.mkdir()

        async with storage_allocator.preallocate_disk_space(source_path.stat().st_size):
            with video_processing_worker as worker:
                # Converting video
                video_info: dict[str, Any] = await current_loop.run_in_executor(
                    worker,
                    self.video_processing.compress_video,
                    source_path,
                    video_dest_dir / "source_video.mp4"
                )

        # Make db record
        async with self.repository.transaction as tr:
            video_dto: VideoDTO = await self.repository.video_repo.create_new_video(
                self.video_processing.get_fps_from_probe(video_info),
                video_dest_dir.relative_to(video_directory).as_posix(),
            )
            await tr.commit()

        return video_dto
