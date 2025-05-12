from typing import Optional

from server.data_storage.dto import ProjectDTO
from server.data_storage.protocols import Repository


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
