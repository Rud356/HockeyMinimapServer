from typing import Optional

from server.data_storage.repository import Repository
from server.models.coordinates import Coordinates


class PlayerData:
    player_coordinates_on_camera: Coordinates
    player_coordinates_on_minimap: Optional[Coordinates]
    player_tracking_id: int
    video_id: int
    frame_id: int
    user_id: Optional[str]
    team_id: Optional[int]
    data_repository: Repository

    async def set_player_position_on_minimap(self, coordinates: Coordinates) -> None:
        ...

    async def rename_tracking_name(self, user_id: str) -> None:
        ...

    async def detect_team(self) -> None:
        ...
