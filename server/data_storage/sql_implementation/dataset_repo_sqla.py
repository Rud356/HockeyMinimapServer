from typing import Optional, cast

from pydantic import ValidationError
from sqlalchemy import Delete, Select, Update, and_, exists, func
from sqlalchemy.engine import TupleResult
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm import selectinload

from server.algorithms.enums import Team
from server.algorithms.enums.player_classes_enum import PlayerClasses
from .tables import Box, Point, SubsetData, TeamsDataset, TeamsSubset
from .transaction_manager_sqla import TransactionManagerSQLA
from ..dto import BoxDTO, DatasetDTO, PointDTO, SubsetDataDTO, TeamsSubsetDTO
from ..dto.subset_data_input import SubsetDataInputDTO
from ..exceptions import DataIntegrityError, NotFoundError
from ..protocols import DatasetRepo


class DatasetRepoSQLA(DatasetRepo):
    def __init__(self, transaction: TransactionManagerSQLA):
        self.transaction: TransactionManagerSQLA = transaction

    async def create_dataset_for_video(self, video_id: int) -> DatasetDTO:
        try:
            new_dataset = TeamsDataset(video_id=video_id)
            async with await self.transaction.start_nested_transaction() as tr:
                tr.session.add(new_dataset)
                await tr.commit()

        except (IntegrityError, ProgrammingError, AttributeError, ValidationError) as err:
            raise DataIntegrityError("Video creation had database constraints broken or data is invalid") from err

        return DatasetDTO(
            dataset_id=new_dataset.dataset_id,
            video_id=new_dataset.video_id,
            subsets=[]
        )

    async def get_team_dataset_by_id(self, dataset_id: int) -> DatasetDTO:
        try:
            dataset: Optional[TeamsDataset] = (await self.transaction.session.execute(
                Select(TeamsDataset)
                .options(selectinload(TeamsDataset.subsets))
                .where(TeamsDataset.dataset_id == dataset_id)
            )).scalar_one_or_none()

        except ProgrammingError as err:
            raise ValueError("Invalid data provided for lookup") from err

        if dataset is None:
            raise NotFoundError("Dataset with provided id was not found")

        subsets: list[TeamsSubsetDTO] = []
        subsets_data: list[TeamsSubset] = dataset.subsets
        for subset in subsets_data:
            subset_data_points: list[SubsetData] = subset.subset_data
            subset_data: list[SubsetDataDTO] = []

            for data_point in subset_data_points:
                data_point_dto: SubsetDataDTO = SubsetDataDTO(
                    tracking_id=data_point.tracking_id,
                    subset_id=data_point.subset_id,
                    frame_id=data_point.frame_id,
                    class_id=data_point.class_id,
                    team_id=data_point.team_id,
                    box=BoxDTO(
                        top_point=PointDTO(
                            x=data_point.box.top_point.x,
                            y=data_point.box.top_point.y
                        ),
                        bottom_point=PointDTO(
                            x=data_point.box.bottom_point.x,
                            y=data_point.box.bottom_point.y
                        ),
                    )
                )
                subset_data.append(data_point_dto)

            subset_data.sort(key=lambda v: v.frame_id)
            subsets.append(
                TeamsSubsetDTO(
                    subset_id=subset.subset_id,
                    from_frame_id=subset.from_frame_id,
                    to_frame_id=subset.to_frame_id,
                    subset_data=subset_data
                )
            )

        return DatasetDTO(
            dataset_id=dataset.dataset_id,
            video_id=dataset.video_id,
            subsets=subsets
        )

    async def add_subset_to_dataset(
        self,
        dataset_id: int,
        from_frame: int,
        to_frame: int,
        subset_data: list[list[SubsetDataInputDTO]]
    ) -> int:
        if from_frame < 0:
            raise ValueError("Invalid from_frame number")

        if to_frame < from_frame:
            raise ValueError("Parameter to_frame can't be less than from_frame")

        if len(subset_data) != (to_frame - from_frame):
            raise ValueError(
                f"Invalid subset_data list length: got {len(subset_data)}, expected {to_frame - from_frame}"
            )

        try:
            dataset: Optional[TeamsDataset] = (await self.transaction.session.execute(
                Select(TeamsDataset)
                .where(TeamsDataset.dataset_id == dataset_id)
            )).scalar_one_or_none()

        except ProgrammingError as err:
            raise ValueError("Invalid data provided for lookup") from err

        if dataset is None:
            raise NotFoundError("Dataset with provided id was not found")

        try:
            async with await self.transaction.start_nested_transaction() as tr:
                new_subset = TeamsSubset(
                    dataset_id=dataset.dataset_id,
                    video_id=dataset.video_id,
                    from_frame_id=from_frame,
                    to_frame_id=to_frame
                )
                tr.session.add(new_subset)

                for n, frame_data in enumerate(subset_data):
                    for data_point in frame_data:
                        subset_data_record: SubsetData = SubsetData(
                            tracking_id=data_point.tracking_id,
                            video_id=dataset.video_id,
                            frame_id=from_frame+n,
                            team_id=data_point.team_id,
                            class_id=data_point.class_id,
                            box=Box(
                                top_point=Point(
                                    x=data_point.box.top_point.x,
                                    y=data_point.box.top_point.y
                                ),
                                bottom_point=Point(
                                    x=data_point.box.top_point.x,
                                    y=data_point.box.top_point.y
                                )
                            )
                        )
                        new_subset.subset_data.append(subset_data_record)

                await tr.commit()
        except (IntegrityError, ProgrammingError) as err:
            raise DataIntegrityError("Invalid data provided") from err

        return new_subset.subset_id

    async def set_player_team(self, subset_id: int, tracking_id: int, team: Team) -> bool:
        dataset_points_found: bool = await self._data_point_exists(subset_id, tracking_id)

        if not dataset_points_found:
            raise NotFoundError()

        async with await self.transaction.start_nested_transaction() as tr:
            await tr.session.execute(
                Update(SubsetData).where(
                    and_(
                        SubsetData.subset_id == subset_id,
                        SubsetData.tracking_id == tracking_id,
                        SubsetData.class_id != PlayerClasses.Referee
                    )
                ).values(team_id=team)
            )
            await tr.commit()

        return True

    async def set_player_class(self, subset_id: int, tracking_id: int, player_class: PlayerClasses) -> bool:
        dataset_points_found: bool = await self._data_point_exists(subset_id, tracking_id)

        if not dataset_points_found:
            raise NotFoundError()

        async with await self.transaction.start_nested_transaction() as tr:
            await tr.session.execute(
                Update(SubsetData).where(
                    and_(
                        SubsetData.subset_id == subset_id,
                        SubsetData.tracking_id == tracking_id
                    )
                ).values(class_id=player_class)
            )
            await tr.commit()

        return True

    async def kill_tracking(self, subset_id: int, tracking_id: int, frame_id: int) -> int:
        dataset_points_found: bool = await self._data_point_exists(subset_id, tracking_id)

        if not dataset_points_found:
            raise NotFoundError()

        async with await self.transaction.start_nested_transaction() as tr:
            deleted = await tr.session.execute(
                Delete(SubsetData).where(
                    and_(
                        SubsetData.subset_id == subset_id,
                        SubsetData.tracking_id == tracking_id,
                        SubsetData.frame_id >= frame_id
                    )
                )
            )
            await tr.commit()

        return cast(int, deleted.rowcount)

    async def get_teams_dataset_size(self, dataset_id: int) -> dict[Team, int]:
        try:
            dataset: Optional[TeamsDataset] = (await self.transaction.session.execute(
                Select(TeamsDataset)
                .where(TeamsDataset.dataset_id == dataset_id)
            )).scalar_one_or_none()

        except ProgrammingError as err:
            raise ValueError("Invalid data provided for lookup") from err

        if dataset is None:
            raise NotFoundError("Dataset with provided id was not found")

        query: Select[tuple[tuple[Team, int], ...]] = Select(
            SubsetData.team_id, func.count(SubsetData.team_id)
        ).join(TeamsSubset, SubsetData.subset_id == TeamsSubset.subset_id).where(
            and_(
                SubsetData.team_id.is_not(None),
                TeamsSubset.dataset_id == dataset.dataset_id,
                SubsetData.class_id != PlayerClasses.Referee
        )).group_by(SubsetData.team_id)
        results: TupleResult[tuple[tuple[Team, int], ...]] = (await self.transaction.session.execute(query)).tuples()

        return {Team.Home: 0, Team.Away: 0} | {
            result[0]: result[1]
            for result in cast(tuple[tuple[Team, int], ...], results)
        }

    async def _data_point_exists(self, subset_id: int, tracking_id: int) -> bool:
        """
        Существует ли запись с предоставленным номером отслеживания в поднаборе данных.
        :param subset_id: Идентификатор поднабора.
        :param tracking_id: Идентификатор отслеживания.
        :return: Есть ли данное отслеживание в БД.
        """
        records_exist: bool | None = await self.transaction.session.scalar(
            Select(exists(SubsetData))
            .where(
                and_(
                    SubsetData.subset_id == subset_id,
                    SubsetData.tracking_id == tracking_id
                )
            )
        )
        if records_exist:
            return True

        return False
