from typing import Optional, cast

from pydantic import ValidationError
from sqlalchemy import Select
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncScalarResult

from server.data_storage.dto import ProjectDTO
from server.data_storage.exceptions import DataIntegrityError, NotFoundError
from server.data_storage.protocols import ProjectRepo
from server.data_storage.sql_implementation.tables import Project
from server.data_storage.sql_implementation.transaction_manager_sqla import TransactionManagerSQLA


class ProjectRepoSQLA(ProjectRepo):
    def __init__(self, transaction: TransactionManagerSQLA):
        self.transaction: TransactionManagerSQLA = transaction

    async def create_project(
        self,
        for_video_id: int,
        name: str,
        team_home_name: Optional[str] = None,
        team_away_name: Optional[str] = None
    ) -> ProjectDTO:
        try:
            new_project: Project = Project(
                for_video_id=for_video_id,
                name=name,
                team_home_name=team_home_name,
                team_away_name=team_away_name
            )

            async with await self.transaction.start_nested_transaction() as tr:
                tr.session.add(new_project)
                await tr.commit()

        except (ProgrammingError, IntegrityError) as err:
            raise DataIntegrityError("Invalid values provided for creating project") from err

        return ProjectDTO(
            project_id=new_project.project_id,
            for_video_id=new_project.for_video_id,
            name=new_project.name,
            created_at=new_project.created_at,
            team_home_name=new_project.team_home_name,
            team_away_name=new_project.team_away_name
        )

    async def edit_project(
        self,
        project_id: int,
        name: Optional[str] = None,
        team_home_name: Optional[str] = None,
        team_away_name: Optional[str] = None
    ) -> ProjectDTO:
        try:
            async with await self.transaction.start_nested_transaction() as tr:
                editing_project: Optional[Project] = await self._get_project(project_id)

                if editing_project is None:
                    raise NotFoundError("Project with specified ID was not found")

                if name:
                    editing_project.name = name

                if team_home_name:
                    editing_project.team_home_name = team_home_name

                if team_away_name:
                    editing_project.team_away_name = team_away_name

                await tr.commit()

        except (ProgrammingError, IntegrityError) as err:
            raise DataIntegrityError("Invalid data for modification provided") from err

        return ProjectDTO(
            project_id=editing_project.project_id,
            for_video_id=editing_project.for_video_id,
            name=cast(str, editing_project.name),
            created_at=editing_project.created_at,
            team_home_name=cast(str, editing_project.team_home_name),
            team_away_name=cast(str, editing_project.team_away_name)
        )

    async def get_projects(self, limit: int = 100, offset: int = 0) -> list[ProjectDTO]:
        query: Select[tuple[Project, ...]] = Select(Project).limit(limit).offset(offset).order_by(Project.created_at)
        result: AsyncScalarResult[Project] = await self.transaction.session.stream_scalars(query)

        projects: list[ProjectDTO] = []
        async for project_record in result:
            try:
                projects.append(
                    ProjectDTO(
                        project_id=project_record.project_id,
                        for_video_id=project_record.for_video_id,
                        name=project_record.name,
                        created_at=project_record.created_at,
                        team_home_name=project_record.team_home_name,
                        team_away_name=project_record.team_away_name
                    )
                )
            except ValidationError:
                continue

        return projects

    async def get_project(self, project_id: int) -> ProjectDTO:
        try:
            result: Optional[Project] = await self._get_project(project_id)

        except ProgrammingError:
            raise ValueError("Invalid data was provided as input")

        if result is None:
            raise NotFoundError("Project with provided id was not found")

        try:
            return ProjectDTO(
                project_id=result.project_id,
                for_video_id=result.for_video_id,
                name=result.name,
                created_at=result.created_at,
                team_home_name=result.team_home_name,
                team_away_name=result.team_away_name
            )

        except ValidationError:
            raise NotFoundError("Project had invalid data when unpacking")

    async def _get_project(self, project_id: int) -> Project:
        """
        Получает объект записи проекта.

        :param project_id: Идентификатор проекта.
        :return: Объект проекта.
        """
        result: Optional[Project] = (await self.transaction.session.execute(
            Select(Project).where(Project.project_id == project_id)
        )).scalar_one_or_none()

        return result
