from pathlib import Path
from typing import Optional

from pydantic import BaseModel, field_validator, validator

from server.algorithms.enums.camera_position import CameraPosition


class VideoDTO(BaseModel):
    video_id: int
    fps: float
    corrective_coefficient_k1: float
    corrective_coefficient_k2: float
    camera_position: CameraPosition
    is_converted: bool
    is_processed: bool
    source_video_path: Path
    converted_video_path: Optional[Path]
    dataset_id: Optional[int]

    @field_validator('source_video_path', 'converted_video_path', mode='before')
    def convert_to_path(cls, value):
        if isinstance(value, str):
            return Path(value)
        return value
