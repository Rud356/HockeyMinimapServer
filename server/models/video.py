from pathlib import Path
from typing import Optional

from server.algorithms.field_detection import FieldDetection
from server.algorithms.player_tracking_test import PlayerTracker
from server.data_storage.repository import Repository
from server.models.frame import Frame
from server.models.field_data import FieldData
from server.views.dto.frame_dto import FrameDTO


class Video:
    video_id: int
    frames: list[Frame]
    video_path: Path
    is_processed: bool
    is_converted: bool
    corrective_coefficient: float
    camera_position: int
    field_data_cache: Optional[FieldData]
    tracking_algorithm: PlayerTracker
    field_detection_algorithm: FieldDetection
    data_repository: Repository

    @classmethod
    async def create_video(
        cls, video_path: Path, data_repository: Repository
    ) -> "Video":
        ...

    @classmethod
    async def import_video(
        cls, video_path: Path,
        data_repository: Repository, frame_data: list[FrameDTO]
    ) -> "Video":
        ...

    @classmethod
    async def load_by_id(
        cls, video_id: int, data_repository: Repository
    ) -> "Video":
        ...

    async def set_corrective_coefficient(self, coefficient: float) -> None:
        ...

    async def render_example(self, frame_id: int) -> Frame:
        ...

    async def convert(self) -> bool:
        ...

    async def frames_processed_callback(self) -> None:
        ...

    async def save_video_state(self) -> None:
        ...
