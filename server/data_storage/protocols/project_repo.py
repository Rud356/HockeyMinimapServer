from typing import Optional, Protocol, runtime_checkable

from server.data_storage.dto.project_dto import ProjectDTO
from server.data_storage.protocols import TransactionManager


@runtime_checkable
class ProjectRepo(Protocol):
    """
    Управляет данными о проектах.
    """
    transaction: TransactionManager

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
        """

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
        """

    async def get_projects(self, limit: int = 100, offset: int = 0) -> list[ProjectDTO]:
        """
        Возвращает список всех проектов.

        :param limit: Сколько проектов получить.
        :param offset: Сколько проектов отступить от начала.
        :return: Список проектов.
        """

    async def get_project(self, project_id: int) -> ProjectDTO:
        """
        Получает конкретный проект под идентификатором.

        :param project_id: Идентификатор проекта.
        :return: Данные о проекте.
        """
