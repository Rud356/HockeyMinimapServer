from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from .dataset_repo_sqla import DatasetRepoSQLA
from .frames_repo_sqla import FramesRepoSQLA
from .map_data_repo_sqla import MapDataRepoSQLA
from .player_data_repo_sqla import PlayerDataRepoSQLA
from .project_repo_sqla import ProjectRepoSQLA
from .tables.base import Base
from .transaction_manager_sqla import TransactionManagerSQLA
from .user_repo_sqla import UserRepoSQLA
from .video_repo_sqla import VideoRepoSQLA
from ..dto import DatasetDTO, FrameDataDTO, MinimapDataDTO, ProjectDTO, ProjectExportDTO, SubsetDataInputDTO, VideoDTO
from ..dto.player_alias import PlayerAlias
from ..exceptions import NotFoundError
from ..protocols import Repository
from ...views.exceptions import InvalidProjectState


class RepositorySQLA(Repository):
    def __init__(self, transaction: TransactionManagerSQLA):
        self.transaction: TransactionManagerSQLA = transaction

    @property
    def player_data_repo(self) -> PlayerDataRepoSQLA:
        return PlayerDataRepoSQLA(self.transaction)

    @property
    def dataset_repo(self) -> DatasetRepoSQLA:
        return DatasetRepoSQLA(self.transaction)

    @property
    def frames_repo(self) -> FramesRepoSQLA:
        return FramesRepoSQLA(self.transaction)

    @property
    def user_repo(self) -> UserRepoSQLA:
        return UserRepoSQLA(self.transaction)

    @property
    def video_repo(self) -> VideoRepoSQLA:
        return VideoRepoSQLA(self.transaction)

    @property
    def map_data_repo(self) -> MapDataRepoSQLA:
        return MapDataRepoSQLA(self.transaction)

    @property
    def project_repo(self) -> ProjectRepoSQLA:
        return ProjectRepoSQLA(self.transaction)

    async def export_project_data(self, project_id: int) -> ProjectExportDTO:
        project: ProjectDTO = await self.project_repo.get_project(project_id)
        video: VideoDTO | None = await self.video_repo.get_video(project.for_video_id)

        if video is None:
            raise NotFoundError("Video linked to project not found in DB")

        if not video.is_converted or not video.is_processed:
            raise InvalidProjectState("Project is in progress of being processed")

        if video.dataset_id is None:
            raise InvalidProjectState("Project must have already been processed, but missing dataset")

        if video.converted_video_path is None:
            raise InvalidProjectState("Project must have already been processed, but not corrected")

        video.source_video_path = Path(video.source_video_path).name
        video.converted_video_path = Path(video.converted_video_path).name

        minimap_data: list[
            MinimapDataDTO
        ] = await self.map_data_repo.get_points_mapping_for_video(
            video.video_id
        )
        frame_data: FrameDataDTO = await self.player_data_repo.get_all_tracking_data(
            video.video_id
        )
        teams_dataset: DatasetDTO = await self.dataset_repo.get_team_dataset_by_id(
            video.dataset_id
        )
        players_aliases: list[PlayerAlias] = list(
            (
                await self.player_data_repo.get_user_alias_for_players(video.video_id)
            ).values()
        )

        return ProjectExportDTO(
            video_data=video,
            project_header=project,
            frame_data=frame_data,
            teams_dataset=teams_dataset,
            minimap_data=minimap_data,
            players_aliases=players_aliases
        )

    async def import_project_data(
        self,
        static_path: Path,
        new_video_folder: Path,
        project_data: ProjectExportDTO
    ) -> ProjectDTO:
        # Restore video in database
        async with await self.transaction.start_nested_transaction() as tr:
            video_data: VideoDTO = project_data.video_data

            if video_data.source_video_path is None or video_data.converted_video_path is None:
                raise ValueError("Video paths must not be empty")

            new_video: VideoDTO = await self.video_repo.create_new_video(
                video_data.fps,
                (new_video_folder / video_data.source_video_path).relative_to(new_video_folder.parent)
            )
            await self.video_repo.adjust_corrective_coefficients(
                new_video.video_id,
                video_data.corrective_coefficient_k1,
                video_data.corrective_coefficient_k2
            )
            await self.video_repo.set_camera_position(
                new_video.video_id,
                project_data.video_data.camera_position
            )

            await self.video_repo.set_flag_video_is_converted(
                new_video.video_id,
                True,
                static_path / "videos",
                new_video_folder / video_data.converted_video_path
            )
            await self.video_repo.set_flag_video_is_processed(new_video.video_id, True)
            await tr.commit()

        # Restore frames in database
        await self.frames_repo.create_frames(
            new_video.video_id, project_data.frame_data.to_frame+1
        )

        # Restore mapped points
        await self.map_data_repo.create_point_mapping_for_video(
            new_video.video_id,
            {
                mapped_point.point_on_minimap: mapped_point.point_on_camera
                    for mapped_point in project_data.minimap_data
            }
        )

        # Restore dataset
        new_dataset = await self.dataset_repo.create_dataset_for_video(new_video.video_id)
        for subset in project_data.teams_dataset.subsets:
            subset_temp_format: dict[int, list[SubsetDataInputDTO]] = {
                frame_id: []
                    for frame_id in range(subset.from_frame_id, subset.to_frame_id)
            }

            for subset_data_point in subset.subset_data:
                subset_temp_format.setdefault(
                    subset_data_point.frame_id,
                    []
                ).append(
                    SubsetDataInputDTO(
                        tracking_id=subset_data_point.tracking_id,
                        frame_id=subset_data_point.frame_id,
                        class_id=subset_data_point.class_id,
                        team_id=subset_data_point.team_id,
                        box=subset_data_point.box
                    )
                )

            await self.dataset_repo.add_subset_to_dataset(
                new_dataset.dataset_id,
                subset.from_frame_id,
                subset.to_frame_id,
                [subset_temp_format[keyframe] for keyframe in sorted(subset_temp_format.keys())]
            )

        # Restore player aliases
        aliases_id_mapping: dict[int, int] = {} # maps old ID onto new ID
        for alias in project_data.players_aliases:
            new_alias_id: int = await self.player_data_repo.create_user_alias_for_players(
                new_video.video_id,
                alias.player_name,
                alias.player_team
            )
            aliases_id_mapping[alias.alias_id] = new_alias_id

        # Assign new ids
        for frame in project_data.frame_data.frames:
            for record in frame:
                if record.player_id:
                    record.player_id = aliases_id_mapping.get(record.player_id)

        # Restore players data
        await self.player_data_repo.insert_player_data(
            new_video.video_id,
            project_data.frame_data.frames
        )

        # Create a project linking the video
        new_project: ProjectDTO = await self.project_repo.create_project(
            new_video.video_id,
            project_data.project_header.name,
            project_data.project_header.team_home_name,
            project_data.project_header.team_away_name
        )
        return new_project

    @staticmethod
    async def init_db(engine: AsyncEngine) -> None:
        """
        Инициализирует БД.

        :type engine: Подключение к базе данных.
        :return: Ничего.
        """
        async with engine.begin() as conn:
            if engine.dialect.name == 'sqlite':
                await conn.execute(text("PRAGMA foreign_keys=ON"))
                await conn.execute(text("PRAGMA journal_mode=WAL;"))

            await conn.run_sync(Base.metadata.create_all)

    @staticmethod
    async def drop_db(engine: AsyncEngine) -> None:
        """
        Удаляет все данные из БД.

        :type engine: Подключение к базе данных.
        :return: Ничего.
        """
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
