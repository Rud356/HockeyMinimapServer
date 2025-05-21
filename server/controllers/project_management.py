from pathlib import Path
from typing import Annotated

from dishka import FromDishka
from fastapi import APIRouter, HTTPException, Query

from server.controllers.dto.create_project import CreateProject
from server.controllers.dto.edit_project import EditProject
from server.controllers.endpoints_base import APIEndpoint
from server.data_storage.dto import ProjectDTO, UserDTO
from server.data_storage.exceptions import DataIntegrityError, NotFoundError
from server.data_storage.protocols import Repository
from server.utils.config import AppConfig
from server.utils.file_lock import FileLock
from server.utils.providers import StaticDirSpaceAllocator
from server.views.exceptions import InvalidProjectState
from server.views.project_view import ProjectView


class ProjectManagementEndpoint(APIEndpoint):
    """
    Описывает эндпоинт взаимодействия с проектами.
    """

    def __init__(self, router: APIRouter):
        super().__init__(router)
        self.router.add_api_route(
            "/projects/",
            self.create_project,
            methods=["post"],
            description="Создает новый проект",
            tags=["projects"],
            responses={
                400: {"description": "Не найдено привязываемое к проекту видео"},
                401: {"description": "Нет валидного токена, или прав на создание проекта"},
            }
        )
        self.router.add_api_route(
            "/projects/",
            self.get_projects,
            methods=["get"],
            description="Получает список проектов разметки",
            tags=["projects"],
            responses={
                401: {"description": "Нет валидного токена пользователя"}
            }
        )
        self.router.add_api_route(
            "/projects/{project_id}",
            self.get_project_by_id,
            description="Получает информацию о существующем проекте",
            tags=["projects"],
            responses={
                400: {"description": "Невалидные данные для поиска"},
                401: {"description": "Нет валидного токена, или прав на создание проекта"},
                404: {"description": "Проект не найден"}
            }
        )
        self.router.add_api_route(
            "/projects/{project_id}",
            self.edit_project,
            methods=["patch"],
            tags=["projects"],
            description="Изменяет существующий проект",
            responses={
                400: {"description": "Невалидные данные для изменения"},
                401: {"description": "Нет валидного токена пользователя"},
                404: {"description": "Проект не найден"}
            }
        )
        self.router.add_api_route(
            "/projects/{project_id}/export",
            self.export_project_by_id,
            methods=["get"],
            tags=["projects"],
            description="Экспортирует данные о проекте в файл export.zip в папке с видео проекта",
            responses={
                400: {"description": "Невалидные данные для запроса"},
                401: {"description": "Нет валидного токена пользователя"},
                409: {"description": "Проект не обработан полностью"},
                425: {"description": "Данные проекта находятся в обработке и не могут быть добавлены в список"}
            }
        )

    async def create_project(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        project_creation_body: CreateProject
    ) -> ProjectDTO:
        """
        Создает новый проект.

        :param repository: Объект взаимодействия с проектом.
        :param current_user: Текущий пользователь системы.
        :param project_creation_body: Тело запроса на создание проекта.
        :return: Данные проекта.
        """
        if not current_user.user_permissions.can_create_projects:
            raise HTTPException(
                401, "No premissions to create projects"
            )

        try:
            return await ProjectView(repository).create_project(
                for_video_id=project_creation_body.for_video_id,
                name=project_creation_body.name,
                team_away_name=project_creation_body.team_away_name,
                team_home_name=project_creation_body.team_home_name
            )

        except DataIntegrityError:
            raise HTTPException(
                400, "Not found linked video"
            )

    async def edit_project(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        project_id: int,
        edit_project_body: EditProject
    ) -> ProjectDTO:
        """
        Изменяет существующий проект.

        :param repository: Объект взаимодействия с проектом.
        :param current_user: Текущий пользователь системы.
        :param project_id: Идентификатор проекта.
        :param edit_project_body: Тело с новыми значениями для изменения.
        :return: Данные проекта.
        """
        if not current_user.user_permissions.can_create_projects:
            raise HTTPException(
                401, "No premissions to edit projects"
            )

        try:
            return await ProjectView(repository).edit_project(
                project_id=project_id,
                name=edit_project_body.name,
                team_away_name=edit_project_body.team_away_name,
                team_home_name=edit_project_body.team_home_name
            )

        except DataIntegrityError:
            raise HTTPException(
                400, "Invalid project data provided"
            )

        except NotFoundError:
            raise HTTPException(
                404, "Project not found"
            )

    async def get_project_by_id(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        project_id: int
    ) -> ProjectDTO:
        """
        Получает информацию о конкретном проекте.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь системы.
        :param project_id: Идентификатор проекта.
        :return: Данные о проекте.
        """
        try:
            return await ProjectView(repository).get_project(project_id)

        except ValueError:
            raise HTTPException(
                400, "Invalid project request"
            )

        except NotFoundError:
            raise HTTPException(
                404, "Project not found"
            )

    async def get_projects(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0
    ) -> list[ProjectDTO]:
        """
        Получает несколько проектов списком.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь системы.
        :param limit: Сколько записей получить.
        :param offset: Сколько записей отступить от начала.
        :return: Список проектов разметки.
        """
        try:
            return await ProjectView(repository).get_projects(
                limit, offset
            )

        except ValueError:
            raise HTTPException(
                400, "Invalid project request"
            )

        except NotFoundError:
            raise HTTPException(
                404, "Project not found"
            )

    async def export_project_by_id(
        self,
        app_config: FromDishka[AppConfig],
        file_lock: FromDishka[FileLock],
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        dest_disk_space_allocator: FromDishka[StaticDirSpaceAllocator],
        project_id: int
    ) -> None:
        """
        Выводит всю информацию о конкретном проекте в виде архива.

        :param dest_disk_space_allocator: Аллокатор свободного места на конечном диске.
        :param app_config: Конфигурация приложения.
        :param file_lock: Блокировщик доступа к файлам.
        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь системы.
        :param project_id: Идентификатор проекта.
        :return: Данные о проекте.
        """
        try:
            await ProjectView(repository).export_project_data(
                app_config.static_path,
                project_id,
                file_lock,
                dest_disk_space_allocator
            )
            return

        except ValueError:
            raise HTTPException(
                400, "Invalid project request"
            )

        except NotFoundError:
            raise HTTPException(
                404, "Project not found"
            )

        except TimeoutError:
            raise HTTPException(
                425, "Project is currently locked for processing"
            )

        except InvalidProjectState:
            raise HTTPException(
                409, "Project is not completed to be processed"
            )
