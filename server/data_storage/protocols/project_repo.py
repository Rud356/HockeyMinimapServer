from typing import Optional, Protocol, runtime_checkable

from server.data_storage.dto.project_dto import ProjectDTO


@runtime_checkable
class ProjectRepo(Protocol):
    """
    Управляет данными о проектах.
    """

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

    async def get_all_projects(self) -> list[ProjectDTO]:
        """
        Возвращает список всех проектов.

        :return: Список проектов.
        """

