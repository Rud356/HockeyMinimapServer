from typing import Optional, Sequence, cast

from sqlalchemy import Delete, Select, Update, and_, exists, func
from sqlalchemy.engine import TupleResult
from sqlalchemy.exc import IntegrityError, NoResultFound, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncScalarResult
from sqlalchemy.orm import selectinload

from server.algorithms.enums import Team
from server.algorithms.enums.player_classes_enum import PlayerClasses
from .tables import Frame, Player, PlayerData, SubsetData
from .tables.team_assignment import TeamAssignment
from .transaction_manager_sqla import TransactionManagerSQLA
from ..dto import FrameDataDTO
from ..dto.player_data_dto import PlayerDataDTO
from ..exceptions import DataIntegrityError, NotFoundError
from ..protocols import PlayerDataRepo


class PlayerDataRepoSQLA(PlayerDataRepo):
    def __init__(self, transaction: TransactionManagerSQLA):
        self.transaction: TransactionManagerSQLA = transaction

    async def insert_player_data(
        self,
        video_id: int,
        players_data_on_frame: list[list[PlayerDataDTO]]
    ) -> None:
        # Get last frame of sequence and if it doesn't exist - error out
        assigned_teams: dict[int, Team | None] = {}
        frame: Frame = await self._get_video_frame(video_id, len(players_data_on_frame) - 1)

        async with await self.transaction.start_nested_transaction() as tr:
            for frame_id, frame_data in enumerate(players_data_on_frame):
                players: list[PlayerData] = []
                for data_point in frame_data:
                    player_data_record: PlayerData = PlayerData(
                        tracking_id=data_point.tracking_id,
                        video_id=frame.video_id,
                        frame_id=frame_id,
                        class_id=data_point.class_id,
                        player_on_camera_top_x=data_point.player_on_camera.top_point.x,
                        player_on_camera_top_y=data_point.player_on_camera.top_point.y,
                        player_on_camera_bottom_x=data_point.player_on_camera.top_point.x,
                        player_on_camera_bottom_y=data_point.player_on_camera.top_point.y,
                        point_on_minimap_x=data_point.player_on_minimap.x,
                        point_on_minimap_y=data_point.player_on_minimap.y
                    )
                    is_not_referee: bool = data_point.class_id != PlayerClasses.Referee
                    if is_not_referee and (assigned_teams.get(data_point.tracking_id) is None):
                        # Save once and cache it to not overwrite same data or cause conflicts
                        assigned_teams[data_point.tracking_id] = data_point.team_id
                        player_data_record.team = TeamAssignment(
                            tracking_id=data_point.tracking_id,
                            video_id=video_id,
                            frame_id=frame_id,
                            team_id=data_point.team_id
                        )

                    players.append(player_data_record)

                tr.session.add_all(players)
                if frame_id % 100 == 0:
                    try:
                        await tr.session.flush()

                    except(IntegrityError, ProgrammingError, NotFoundError) as err:
                        await tr.rollback()
                        raise DataIntegrityError("Invalid data provided") from err

            try:
                await tr.commit()

            except (IntegrityError, ProgrammingError, NotFoundError) as err:
                raise DataIntegrityError("Invalid data provided") from err

    async def kill_tracking(self, video_id: int, frame_id: int, tracking_id: int) -> int:
        if not await self._does_video_frame_data_exists(video_id, tracking_id):
            raise NotFoundError("Records for specified tracks not found")

        async with await self.transaction.start_nested_transaction() as tr:
            deleted = await tr.session.execute(
                Delete(PlayerData).where(
                    and_(
                        PlayerData.video_id == video_id,
                        PlayerData.tracking_id == tracking_id,
                        PlayerData.frame_id >= frame_id
                    )
                )
            )
            await tr.commit()

        return cast(int, deleted.rowcount)

    async def kill_all_tracking_of_player(self, video_id: int, tracking_id: int) -> int:
        if not await self._does_video_frame_data_exists(video_id, tracking_id):
            raise NotFoundError("Records for specified tracks not found")

        async with await self.transaction.start_nested_transaction() as tr:
            deleted = await tr.session.execute(
                Delete(PlayerData).where(
                    and_(
                        PlayerData.video_id == video_id,
                        PlayerData.tracking_id == tracking_id
                    )
                )
            )
            await tr.commit()

        return cast(int, deleted.rowcount)

    async def set_player_class_to_tracking_id(
        self, video_id: int, frame_id: int, tracking_id: int, class_id: PlayerClasses
    ) -> int:
        if not await self._does_video_frame_data_exists(video_id, tracking_id):
            raise NotFoundError("Tracking id not found")

        async with await self.transaction.start_nested_transaction() as tr:
            result = await tr.session.execute(
                Update(PlayerData).where(
                    and_(
                        PlayerData.video_id == video_id,
                        PlayerData.tracking_id == tracking_id
                    )
                ).values(class_id=class_id)
            )
            await tr.commit()

        return cast(int, result.rowcount)

    async def set_team_to_tracking_id(
        self, video_id: int, frame_id: int, tracking_id: int, team: Team
    ) -> None:
        player_data: Optional[PlayerData] = (await self.transaction.session.scalars(
            Select(PlayerData)
            .where(
                and_(
                    PlayerData.video_id == video_id,
                    PlayerData.tracking_id == tracking_id
                )
            )
        )).first()

        if player_data is None:
            raise NotFoundError("Player tracking data was not found")

        async with await self.transaction.start_nested_transaction() as tr:
            if player_data.team is not None:
                player_data.team.team_id = team

            else:
                player_data.team = TeamAssignment(
                    tracking_id=tracking_id,
                    video_id=video_id,
                    frame_id=frame_id,
                    team_id=team
                )

            await tr.commit()

    async def get_user_ids_for_players(self, video_id: int) -> dict[int, str | None]:
        players_ids: Sequence[Player] = (await self.transaction.session.scalars(
            Select(Player).where(Player.video_id == video_id)
        )).all()

        return {
            player_id.player_id: player_id.user_id for player_id in players_ids
        }

    async def create_user_id_for_players(
        self,
        video_id: int,
        users_player_alias: str,
        player_team: Team | None = None
    ) -> int:
        player_alias: Player = Player(
            video_id=video_id, user_id=users_player_alias, team_id=player_team
        )

        async with await self.transaction.start_nested_transaction() as tr:
            tr.session.add(player_alias)
            try:
                await tr.commit()

            except (ProgrammingError, IntegrityError) as err:
                raise DataIntegrityError("Invalid video ID or some other problem with data") from err

        return player_alias.player_id

    async def delete_player_alias(self, custom_player_id: int) -> bool:
        try:
            async with await self.transaction.start_nested_transaction() as tr:
                player_alias: Player = cast(Player, await tr.session.get_one(Player, custom_player_id))
                await tr.session.delete(player_alias)

        except NoResultFound as err:
            raise NotFoundError("Player alias not found") from err

        return True

    async def rename_player_alias(self, custom_player_id: int, users_player_alias: str) -> None:
        try:
            async with await self.transaction.start_nested_transaction() as tr:
                player_alias: Player = cast(Player, await tr.session.get_one(Player, custom_player_id))
                player_alias.user_id = users_player_alias
                await tr.commit()

        except NoResultFound as err:
            raise NotFoundError("Player alias not found") from err

        except (ProgrammingError, IntegrityError) as err:
            raise DataIntegrityError("Invalid data for modification provided") from err

    async def get_tracking_from_frames(
        self, video_id: int, limit: int = 120, offset: int = 0
    ) -> FrameDataDTO:
        query: Select[tuple[Frame, ...]] = Select(Frame).order_by(
            Frame.frame_id
        ).limit(limit).offset(offset).options(
            selectinload(Frame.player_data)
        ).where(Frame.video_id == video_id)

        result: AsyncScalarResult[Frame] = await self.transaction.session.stream_scalars(query)
        from_frame, to_frame = await self.get_frames_min_and_max_ids_with_limit_offset(video_id, limit, offset)

        frame_data: list[list[PlayerDataDTO]] = []

        async for frame in result:
            frame_data_players: list[PlayerDataDTO] = []
            for player_data in frame.player_data:
                player_name: None | str = None
                if player_data.player is not None:
                    player_name = cast(str | None, player_data.player.user_id)

                team_id: Team | None = None
                if player_data.team is not None:
                    team_id = cast(Team | None, player_data.team.team_id)

                player = PlayerDataDTO(
                    tracking_id=player_data.tracking_id,
                    player_id=player_data.player_id,
                    player_name=player_name,
                    team_id=team_id,
                    class_id=player_data.class_id,
                    player_on_camera=player_data.box,
                    player_on_minimap=player_data.point_on_minimap
                )
                frame_data_players.append(player)

            frame_data.append(frame_data_players)

        return FrameDataDTO(
            from_frame=from_frame,
            to_frame=to_frame,
            frames=frame_data
        )

    async def get_all_tracking_data(self, video_id: int) -> FrameDataDTO:
        query: Select[tuple[Frame, ...]] = Select(Frame).order_by(
            Frame.frame_id
        ).options(
            selectinload(Frame.player_data)
        ).where(Frame.video_id == video_id)

        result: AsyncScalarResult[Frame] = await self.transaction.session.stream_scalars(query)
        from_frame, to_frame = await self.get_frames_min_and_max_ids_in_video(video_id)

        frame_data: list[list[PlayerDataDTO]] = []

        async for frame in result:
            frame_data_players: list[PlayerDataDTO] = []
            for player_data in frame.player_data:
                player_name: None | str = None
                if player_data.player is not None:
                    player_name = cast(str | None, player_data.player.user_id)

                team_id: Team | None = None
                if player_data.team is not None:
                    team_id = cast(Team | None, player_data.team.team_id)

                player = PlayerDataDTO(
                    tracking_id=player_data.tracking_id,
                    player_id=player_data.player_id,
                    player_name=player_name,
                    team_id=team_id,
                    class_id=player_data.class_id,
                    player_on_camera=player_data.box,
                    player_on_minimap=player_data.point_on_minimap
                )
                frame_data_players.append(player)

            frame_data.append(frame_data_players)

        return FrameDataDTO(
            from_frame=from_frame,
            to_frame=to_frame,
            frames=frame_data
        )

    async def set_player_identity_to_user_id(self, video_id: int, tracking_id: int, player_id: int) -> int:
        async with await self.transaction.start_nested_transaction() as tr:
            player_alias = await tr.session.get_one(
                Player, {"player_id": player_id, "video_id": video_id}
            )
            result = await tr.session.execute(
                Update(PlayerData).where(
                    and_(
                        PlayerData.video_id == video_id,
                        SubsetData.tracking_id == tracking_id
                    )
                ).values(player_id=player_alias.player_id)
            )

            try:
                await tr.commit()

            except NoResultFound as err:
                raise NotFoundError("Player or alias were not found") from err

        return cast(int, result.rowcount)

    async def get_frames_min_and_max_ids_in_video(self, video_id: int) -> tuple[int, int]:
        min_frame_number: int
        max_frame_number: int
        result: TupleResult[tuple[int, ...]] = (await self.transaction.session.execute(
            Select(func.min(Frame.frame_id), func.max(Frame.frame_id)).where(
                Frame.video_id == video_id
            )
        )).tuples()
        (min_frame_number, max_frame_number), *_ = tuple(result)

        return min_frame_number, max_frame_number

    async def get_frames_min_and_max_ids_with_limit_offset(
        self, video_id: int, limit: int, offset: int
    ) -> tuple[int, int]:
        min_frame_number: int
        max_frame_number: int
        result = (await self.transaction.session.execute(
            Select(func.min(Frame.frame_id), func.max(Frame.frame_id))
            .where(
                Frame.video_id == video_id,
                Frame.frame_id.between(offset, offset+limit)
            )
        )).one_or_none()

        if result is None:
            raise IndexError("Invalid frame indexes")

        min_frame_number, max_frame_number = result
        return min_frame_number, max_frame_number

    async def _get_video_frame(self, video_id: int, frame_id: int) -> Frame:
        """
        Получает объект кадра из видео.

        :param video_id: Идентификатор видео.
        :param frame_id: Идентификатор кадра.
        :return: Объект кадра.
        """
        try:
            result = await self.transaction.session.get_one(
                Frame, {"video_id": video_id, "frame_id": frame_id}
            )

        except NoResultFound as err:
            raise NotFoundError("Frame of video wasn't found") from err

        return cast(Frame, result)

    async def _does_video_frame_data_exists(self, video_id: int, tracking_id: int):
        records_exist: bool | None = await self.transaction.session.scalar(
            Select(exists(PlayerData))
            .where(
                and_(
                    PlayerData.video_id == video_id,
                    PlayerData.tracking_id == tracking_id
                )
            )
        )

        if records_exist:
            return True

        return False
