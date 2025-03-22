from typing import Protocol, runtime_checkable

from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.enums.team import Team
from server.data_storage.dto.dataset_dto import DatasetDTO
from server.data_storage.dto.teams_subset_dto import TeamsSubsetDTO
from server.data_storage.protocols.transaction_manager import TransactionManager


@runtime_checkable
class DatasetRepo(Protocol):
    transaction: TransactionManager

    async def get_videos_team_dataset(self, video_id: int) -> DatasetDTO:
        ...

    async def set_player_team(self, subset_id: int, tracking_id: int, team: Team) -> bool:
        ...

    async def change_player_class(self, subset_id: int, tracking_id: int, player_class: PlayerClasses) -> bool:
        ...

    async def kill_tracking(self, subset_id: int, tracking_id: int, frame_id: int) -> int:
        ...

    async def get_teams_dataset_size(self, video_id: int) -> dict[Team, int]:
        ...
