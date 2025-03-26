from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from server.algorithms.enums.camera_position import CameraPosition


class VideoDTO(BaseModel):
    video_id: int
    corrective_coefficient_k1: float
    corrective_coefficient_k2: float
    camera_position: CameraPosition
    is_converted: bool
    is_processed: bool
    source_video_path: Path
    converted_video_path: Optional[Path]
    dataset_id: Optional[int]
