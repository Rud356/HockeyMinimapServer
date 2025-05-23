import asyncio
import uuid
import zipfile
from asyncio import AbstractEventLoop
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Optional

import aiofiles
import orjson

from server.data_storage.dto import ProjectDTO, ProjectExportDTO, VideoDTO
from server.data_storage.exceptions import NotFoundError
from server.data_storage.protocols import Repository
from server.utils.file_lock import FileLock
from server.utils.providers import StaticDirSpaceAllocator
from server.views.exceptions import InvalidProjectState


class ProjectView:
    """
    Предоставляет интерфейс работы с проектами.
    """

    def __init__(self, repository: Repository):
        self.repository: Repository = repository

    async def create_project(
        self,
        for_video_id: int,
        name: str,
        team_home_name: Optional[str] = None,
        team_away_name: Optional[str] = None
    ) -> ProjectDTO:
        """
        Создает новый проект для разметки видео.

        :param for_video_id: Идентификатор для видео, которое будет обрабатываться.
        :param name: Имя проекта.
        :param team_home_name: Название домашней команды.
        :param team_away_name: Название гостевой команды.
        :return: Информация о проекте.
        :raises DataIntegrityError: Неверные входные данные для создания проекта.
        """
        async with self.repository.transaction as tr:
            resulting_project: ProjectDTO = await self.repository.project_repo.create_project(
                for_video_id, name, team_home_name, team_away_name
            )
            await tr.commit()

        return resulting_project

    async def edit_project(
        self,
        project_id: int,
        name: Optional[str] = None,
        team_home_name: Optional[str] = None,
        team_away_name: Optional[str] = None
    ) -> ProjectDTO:
        """
        Изменяет данные о проекте.

        :param project_id: Идентификатор изменяемого проекта.
        :param name: Имя проекта.
        :param team_home_name: Имя домашней команды.
        :param team_away_name: Имя гостевой команды.
        :return: Измененный проект.
        :raises NotFoundError: Если не найден проект для изменения.
        :raises DataIntegrityError: Неверные входные данные для изменения проекта.
        """
        async with self.repository.transaction as tr:
            resulting_project: ProjectDTO = await self.repository.project_repo.edit_project(
                project_id, name, team_home_name, team_away_name
            )
            await tr.commit()

        return resulting_project

    async def get_projects(self, limit: int = 100, offset: int = 0) -> list[ProjectDTO]:
        """
        Возвращает список всех проектов.

        :param limit: Сколько проектов получить.
        :param offset: Сколько проектов отступить от начала.
        :return: Список проектов.
        """
        async with self.repository.transaction:
            return await self.repository.project_repo.get_projects(limit, offset)

    async def get_project(self, project_id: int) -> ProjectDTO:
        """
        Получает конкретный проект под идентификатором.

        :param project_id: Идентификатор проекта.
        :return: Данные о проекте.
        :raise NotFoundError: Не найдено валидного проекта с таким идентификатором.
        :raise ValueError: Неправильные входные данные.
        """
        async with self.repository.transaction:
            return await self.repository.project_repo.get_project(project_id)

    async def export_project_data(
        self,
        static_path: Path,
        project_id: int,
        file_lock: FileLock,
        dest_disk_space_allocator: StaticDirSpaceAllocator
    ) -> Path:
        """
        Экспортирует данные о проекте и сохраняет их в виде архива.

        :param file_lock: Блокировщик доступа к файлам.
        :param static_path: Путь до статической директории с файлами.
        :param dest_disk_space_allocator: Аллокатор пространства на диске в конечной папке.
        :param project_id: Идентификатор проекта для экспорта.
        :return: Путь до файла с архивом.
        :raise NotFoundError: Не найдено валидного проекта с таким идентификатором.
        :raise ValueError: Неправильные входные данные.
        :raise InvalidProjectState: Проект не обработан для вывода в файл.
        :raise TimeoutError: Не удалось захватить блокировку файла для работы с ним.
        """
        async with self.repository.transaction:
            current_project: ProjectDTO = await self.repository.project_repo.get_project(project_id)
            video: VideoDTO | None = await self.repository.video_repo.get_video(current_project.for_video_id)

        if video is None:
            raise NotFoundError("Video must exist for export to work")

        if video.converted_video_path is None:
            raise InvalidProjectState("Project must have already been processed, but not corrected")

        projects_directory: Path = static_path / "videos"
        video_project_dir: Path = (projects_directory / video.source_video_path).parent

        async with self.repository.transaction:
            project_data: ProjectExportDTO = await self.repository.export_project_data(project_id)

        loop: AbstractEventLoop = asyncio.get_running_loop()
        json_output_path: Path = video_project_dir / "project_data.json"
        source_video_path: Path = projects_directory / video.source_video_path
        converted_video_path: Path = projects_directory / video.converted_video_path
        video_mask: Path = video_project_dir / "field_mask.jpeg"
        exported_zip_path: Path = video_project_dir / "export.zip"

        currently_used_space: int = source_video_path.stat().st_size + converted_video_path.stat().st_size
        file_locks = [
            file_lock.lock_file(json_output_path, timeout=1),
            file_lock.lock_file(source_video_path, timeout=1),
            file_lock.lock_file(video_mask, timeout=1),
        ]

        if source_video_path != converted_video_path:
            file_locks.append(file_lock.lock_file(converted_video_path, timeout=1))

        async with (
            AsyncExitStack() as stack,
            dest_disk_space_allocator.preallocate_disk_space(currently_used_space)
        ):
            for file_locker in file_locks:
                await stack.enter_async_context(file_locker)

            with ThreadPoolExecutor(1) as executor:
                resulting_json: str = await loop.run_in_executor(
                    executor, project_data.model_dump_json
                )
                async with aiofiles.open(json_output_path, mode="w", encoding="utf-8") as f:
                    await f.write(resulting_json)

                with zipfile.ZipFile(exported_zip_path, mode="w") as export:
                    await loop.run_in_executor(
                        executor, export.write,
                        json_output_path,
                        json_output_path.name
                    )
                    await loop.run_in_executor(
                        executor, export.write,
                        source_video_path,
                        source_video_path.name
                    )

                    if source_video_path != converted_video_path:
                        await loop.run_in_executor(
                            executor, export.write,
                            converted_video_path,
                            converted_video_path.name
                        )

                    await loop.run_in_executor(
                        executor, export.write,
                        video_mask,
                        video_mask.name
                    )

        return exported_zip_path

    async def import_project(
        self,
        static_path: Path,
        archive_path: Path,
        dest_disk_space_allocator: StaticDirSpaceAllocator
    ) -> ProjectDTO:
        """
        Получает данные из архива и воссоздает проект в базе данных под новыми идентификаторами.

        :param static_path: Путь до статической директории.
        :param archive_path: Путь до файла архива.
        :param dest_disk_space_allocator: Аллокатор места на диске конечной папки.
        :return: Объект воссозданного проекта.
        :raise FileNotFoundError: Файл не обнаружен в архиве.
        :raise ValidationError: Файл с данными о проекте не обнаружен.
        """
        loop: AbstractEventLoop = asyncio.get_running_loop()

        with ThreadPoolExecutor(1) as executor:
            with zipfile.ZipFile(archive_path, mode="r") as imported_zip:
                filenames: set[str] = set(imported_zip.namelist())
                if "project_data.json" not in filenames:
                    raise FileNotFoundError("project_data.json must be included into archive")

                if "field_mask.jpeg" not in filenames:
                    raise FileNotFoundError("field_mask.jpeg must be included into archive")

                json_text: str = imported_zip.read("project_data.json").decode("utf-8")
                project_data: ProjectExportDTO = ProjectExportDTO(
                    **orjson.loads(json_text)
                )

                if not all(
                    [linked_file in filenames for linked_file in
                      (project_data.video_data.source_video_path, project_data.video_data.converted_video_path)
                    ]
                ):
                    raise FileNotFoundError("Linked file in archive is missing")

                new_uuid: str = str(uuid.uuid1())
                project_dest_path: Path = static_path / new_uuid
                project_dest_path.mkdir()

                # Extracting files
                async with dest_disk_space_allocator.preallocate_disk_space(
                    sum((item.file_size for item in imported_zip.filelist)),
                    over_proposition_factor=1
                ):
                    await loop.run_in_executor(
                        executor,
                        imported_zip.extract,
                        "project_data.json",
                        project_dest_path / "project_data.json"
                    )
                    await loop.run_in_executor(
                        executor,
                        imported_zip.extract,
                        "field_mask.jpeg",
                        project_dest_path / "field_mask.jpeg"
                    )
                    await loop.run_in_executor(
                        executor,
                        imported_zip.extract,
                        project_data.video_data.source_video_path,
                        str(project_dest_path / project_data.video_data.source_video_path)
                    )

                source_file_name: str = project_data.video_data.source_video_path
                converted_file_name: str | None = project_data.video_data.converted_video_path
                are_different_files: bool = source_file_name != converted_file_name
                if are_different_files and (converted_file_name is not None):
                    await loop.run_in_executor(
                        executor,
                        imported_zip.extract,
                        converted_file_name,
                        str(project_dest_path / converted_file_name)
                    )

            async with self.repository.transaction as tr:
                project: ProjectDTO = await self.repository.import_project_data(
                    static_path,
                    project_dest_path,
                    project_data
                )
                await tr.commit()

            return project
