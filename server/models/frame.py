from pathlib import Path
from typing import Optional, TYPE_CHECKING

from server.algorithms.field_detection import FieldDetection
from server.algorithms.player_tracking_test import PlayerTracker
from server.data_storage.repository import Repository
from server.models.field_data import FieldData
from server.models.player_data import PlayerData

if TYPE_CHECKING:
    from server.views.dto.frame_dto import FrameDTO


class Frame:
    video_id: int
    frame_id: int
    video_path: Path
    frame_path: Optional[Path]
    processed: bool
    tracked_players: list[PlayerData]
    field_data: Optional[FieldData]
    camera_position: int
    data_repository: Repository

    def __init__(
        self,
        video_id: int,
        frame_id: int,
        video_path: Path,
        processed: bool,
        camera_position: int,
        data_repository: Repository,
        frame_path: Optional[Path] = None,
        field_data: Optional[FieldData] = None,
        tracked_players: Optional[list[PlayerData]] = None,
    ):
        self.video_id = video_id
        self.frame_id = frame_id
        self.video_path = video_path
        self.frame_path = frame_path
        self.processed = processed
        self.camera_position = camera_position
        self.data_repository = data_repository
        self.field_data = field_data
        self.tracked_players = tracked_players or []

    @classmethod
    async def create_frame(
        cls, frame_number: int, video_id: int, data_repository: Repository
    ) -> "Frame":
        ...

    @classmethod
    async def import_frame(
        cls, frame_number: int, video_id: int,
        frame_data: FrameDTO, data_repository: Repository
    ) -> "Frame":
        ...

    async def process_frame(
        self, tracking_algorithm: PlayerTracker,
        field_detection_algorithm: FieldDetection
    ) -> bool:
        ...

    async def map_player_to_users_name(
        self, player_tracking_id: int, user_id: str
    ) -> None:
        ...

    async def save_frame_state(self) -> bool:
        ...
