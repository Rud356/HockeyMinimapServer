import pathlib
import tempfile
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from typing import Annotated, Optional

import aiofiles
from dishka.integrations.fastapi import FromDishka
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from starlette.responses import FileResponse, HTMLResponse

from server.algorithms.exceptions.invalid_file_format import InvalidFileFormat
from server.algorithms.exceptions.out_of_disk_space import OutOfDiskSpace
from server.algorithms.video_processing import VideoProcessing
from server.controllers.endpoints_base import APIEndpoint
from server.controllers.exceptions import UnauthorizedResourceAccess
from server.data_storage.dto import UserDTO
from server.data_storage.exceptions import DataIntegrityError, NotFoundError
from server.data_storage.protocols import Repository
from server.utils.config import AppConfig
from server.utils.providers import StaticDirSpaceAllocator, TmpDirSpaceAllocator, VideoProcessingWorker
from server.views.video_view import VideoDTO, VideoView


class VideoUploadEndpoint(APIEndpoint):
    def __init__(self, router: APIRouter, video_processing: VideoProcessing):
        super().__init__(router)
        self.video_processing: VideoProcessing = video_processing
        self.router.add_api_route(
            "/videos_upload",
            self.upload_page,
            methods=["get"],
            tags=["video"]
        )
        self.router.add_api_route(
            "/videos",
            self.upload_video,
            description="Загружает новое видео на сервер",
            methods=["post"],
            tags=["video"],
            responses={
                400: {"description": "Неверный размер файла или формат не является видео"},
                500: {"description": "Ошибка сервера во время обработки файла"},
                507: {"description": "Не удалось выделить достаточно места на диске для сохранения файла"}
            }
        )
        self.router.add_api_route(
            "/videos/",
            self.get_videos,
            description="Получает список видео",
            methods=["get"],
            tags=["video"]
        )
        self.router.add_api_route(
            "/videos/{video_id}",
            self.get_video,
            description="Получает информацию о видео по идентификатору",
            methods=["get"],
            tags=["video"],
            responses = {
                400: {"description": "Неверные данные о видео или неверный ID видео"},
                404: {"description": "Видео с предоставленным ID не найдено"},
            }
        )
        self.router.add_api_route(
            "/videos/{video_id}/correction",
            self.get_correction_preview,
            description="Получает пример коррекции видео",
            methods=["get"],
            tags=["video"],
            responses={
                400: {"description": "Неверная временная метка"},
                404: {"description": "Видео с предоставленным ID не найдено или файл утерян/испорчен"},
                500: {"description": "Отсутствует информация о длине видео"}
            }
        )
        self.router.add_api_route(
            "/videos/{video_id}/correction",
            self.change_correction_coefficients,
            description="Изменяет коэффициент коррекции видео",
            methods=["patch"],
            tags=["video"],
            responses={
                400: {"description": "Неверные данные о коэффициенте коррекции"},
                404: {"description": "Видео с предоставленным ID не найдено"},
                409: {"description": "Видео было конвертировано с предыдущими коэффициентами коррекции"}
            }
        )
        self.router.add_api_route(
            "/videos/{video_id}/correction",
            self.apply_correction_to_video,
            description="Применяет коррекцию на все видео",
            methods=["put"],
            tags=["video"],
            responses={
                401: {"description": "Нет прав на выполнение коррекции"},
                404: {"description": "Видео с предоставленным ID не найдено или файл утерян/испорчен"},
                409: {"description": "Видео было конвертировано с текущим коэффициентами коррекции"},
                507: {"description": "Не удалось выделить достаточно места на диске для сохранения файла"}
            }
        )

    async def upload_page(self) -> HTMLResponse:
        return HTMLResponse(content="""
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>File Upload</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f4f4f9;
                }
                .upload-container {
                    background-color: #fff;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                }
                input[type="file"] {
                    margin-bottom: 15px;
                }
                button {
                    padding: 10px 20px;
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                }
                button:hover {
                    background-color: #0056b3;
                }
            </style>
        </head>
        <body>
        
        <div class="upload-container">
            <h2>Upload a File</h2>
            <form action="/api/videos" method="post" enctype="multipart/form-data">
                <input type="file" name="video_upload" id="fileToUpload" required>
                <br>
                <button type="submit">Upload File</button>
            </form>
        </div>
        
        </body>
        </html>
        """, status_code=200)

    async def upload_video(
        self,
        repository: FromDishka[Repository],
        app_config: FromDishka[AppConfig],
        current_user: FromDishka[UserDTO],
        temp_disk_space_allocator: FromDishka[TmpDirSpaceAllocator],
        dest_disk_space_allocator: FromDishka[StaticDirSpaceAllocator],
        video_processing_worker: FromDishka[VideoProcessingWorker],
        video_upload: UploadFile = File(...),
    ) -> VideoDTO | None:
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have access to administrating rights"
            )

        if video_upload.filename is None or video_upload.size is None:
            raise HTTPException(
                status_code=400,
                detail='Invalid file name or file size is not found, expecting valid upload'
            )

        try:
            async with (
                aiofiles.tempfile.TemporaryDirectory(prefix="hmms_uploads_") as tmp_dir,
                temp_disk_space_allocator.preallocate_disk_space(video_upload.size),
            ):
                temp_file: pathlib.Path = pathlib.Path(tmp_dir) / video_upload.filename
                async with aiofiles.open(temp_file, 'wb') as f:
                    while contents := await video_upload.read(1024 * 1024):
                        await f.write(contents)

                return await VideoView(repository).create_new_video_from_upload(
                    temp_file,
                    app_config.static_path / "videos",
                    video_processing_worker,
                    self.video_processing,
                    dest_disk_space_allocator
                )

        except InvalidFileFormat:
            raise HTTPException(status_code=400, detail='Invalid file format, expecting video')

        except OutOfDiskSpace as ran_out_of_disk:
            raise HTTPException(
                status_code=507,
                detail=f"Not enough disk space, only "
                       f"{ran_out_of_disk.free_runtime_disk_space} is currently unreserved"
            )

        except Exception as err:
            raise HTTPException(status_code=500, detail='Something went wrong') from err

        finally:
            await video_upload.close()

    async def get_video(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int
    ) -> VideoDTO:
        """
        Получает информацию о видео.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Пользователь системы.
        :param video_id: Идентификатор видео.
        :return: Объект информации о видео.
        """
        try:
            video: VideoDTO = await VideoView(repository).get_video(video_id)

        except ValueError as err:
            raise HTTPException(
                400,
                "Bad data been received, or video can't be accessed"
            ) from err

        except NotFoundError:
            raise HTTPException(status_code=404, detail="Video not found with provided ID")

        return video

    async def get_videos(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0
    ) -> list[VideoDTO]:
        """
        Получает список видео.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Пользователь системы.
        :param limit: Сколько записей получить.
        :param offset: Сколько записей отступить от начала.
        :return: Список объектов видео.
        """
        videos = await VideoView(repository).get_videos(limit, offset)
        return videos

    async def get_correction_preview(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        app_config: FromDishka[AppConfig],
        video_id: int,
        frame_timestamp: Annotated[Optional[float], Query(ge=0)] = 0.0
    ) -> FileResponse:
        try:
            temp_dir = tempfile.mkdtemp(prefix="hmms_preview_")
            temp_dir_path: Path = Path(temp_dir)
            temp_frame: Path = temp_dir_path / "frame.jpeg"

            await VideoView(repository).generate_correction_preview(
                video_id,
                ThreadPoolExecutor(1),
                self.video_processing,
                app_config.static_path,
                temp_frame,
                frame_timestamp
            )

            return FileResponse(temp_frame.resolve())

        except ValueError:
            raise HTTPException(400, "Bad video timestamp")

        except (FileNotFoundError, InvalidFileFormat):
            raise HTTPException(404, "Video file not found or invalid")

        except NotFoundError:
            raise HTTPException(404, "Video not found with provided ID")

        except KeyError:
            raise HTTPException(500, "Video doesn't have DURATION in metadata, likely corrupted")

    async def change_correction_coefficients(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int,
        k1: Annotated[float, Query(ge=-1, le=1, description="Коэффициент коррекции 1")] = 0,
        k2: Annotated[float, Query(ge=-1, le=1, description="Коэффициент коррекции 2")] = 0,
        override_coefficients_after_convertion: Annotated[
            bool,
            Query(description="Требуется ли перезапись коэффициентов для конвертации снова")
        ] = False
    ) -> VideoDTO:
        """
        Изменяет коэффициенты коррекции видео.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Пользователь системы.
        :param video_id: Идентификатор видео.
        :param k1: Первичный коэффициент коррекции.
        :param k2: Вторичный коэффициент коррекции.
        :param override_coefficients_after_convertion: Перезаписать коэффициенты конвертации.
        :return: Обновленные данные о видео.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            view: VideoView = VideoView(repository)
            await view.adjust_corrective_coefficients(
                video_id, k1, k2, override_coefficients_after_convertion
            )
            video: VideoDTO = await view.get_video(video_id)

        except DataIntegrityError:
            raise HTTPException(
                400,
                "Bad values for coefficients"
            )

        except NotFoundError:
            raise HTTPException(
                404,
                "Video not found"
            )

        except ValueError:
            raise HTTPException(
                409,
                "Video has been already converted"
            )

        return video

    async def apply_correction_to_video(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_processing_worker: FromDishka[VideoProcessingWorker],
        temp_disk_space_allocator: FromDishka[TmpDirSpaceAllocator],
        dest_disk_space_allocator: FromDishka[StaticDirSpaceAllocator],
        app_config: FromDishka[AppConfig],
        video_id: int,
        render_again: Annotated[
            bool,
            Query(description="Требуется ли повторная коррекция для видео")
        ] = False
    ) -> VideoDTO:
        """
        Корректирует все видео в соответствии с коэффициентами.

        :param dest_disk_space_allocator: Аллокатор места в конечной папки для хранения файлов.
        :param temp_disk_space_allocator: Аллокатор места во временной папки для хранения файлов.
        :param video_processing_worker: Обработчик видео в потоках.
        :param app_config: Конфигурация приложения.
        :param repository: Объект взаимодействия с БД.
        :param current_user: Пользователь системы.
        :param video_id: Идентификатор видео.
        :param render_again: Обработать ли видео заново.
        :return: Объект с информацией о видео.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            view: VideoView = VideoView(repository)
            await view.apply_video_correction(
                video_id,
                video_processing_worker,
                self.video_processing,
                app_config.static_path,
                render_again,
                temp_disk_space_allocator,
                dest_disk_space_allocator
            )
            return await view.get_video(video_id)

        except (FileNotFoundError, InvalidFileFormat):
            raise HTTPException(404, "Video file not found or invalid")

        except NotFoundError:
            raise HTTPException(404, "Video not found with provided ID")

        except ValueError:
            raise HTTPException(409, "Video is already corrected and rendered")

        except OutOfDiskSpace as ran_out_of_disk:
            raise HTTPException(
                status_code=507,
                detail=f"Not enough disk space, only "
                       f"{ran_out_of_disk.free_runtime_disk_space} is currently unreserved"
            )
