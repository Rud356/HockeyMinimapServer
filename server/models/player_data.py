from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
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

    def __init__(
        self,
        video_id: int,
        frame_id: int,
        player_coordinates_on_camera: Coordinates,
        player_tracking_id: int,
        data_repository: Repository,
        player_coordinates_on_minimap: Optional[Coordinates] = None,
        user_id: Optional[str] = None,
        team_id: Optional[int] = None
    ):
        self.video_id = video_id
        self.frame_id = frame_id
        self.player_coordinates_on_camera = player_coordinates_on_camera
        self.player_tracking_id = player_tracking_id
        self.data_repository = data_repository
        self.player_coordinates_on_minimap = player_coordinates_on_minimap
        self.user_id = user_id
        self.team_id = team_id

    async def set_player_position_on_minimap(
        self, coordinates: Coordinates
    ) -> None:
        ...

    async def rename_tracking_name(self, user_id: str) -> None:
        ...

    async def detect_team(self) -> None:
        ...
