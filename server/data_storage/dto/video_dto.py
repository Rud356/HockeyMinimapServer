from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, field_validator

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
    def convert_to_path(cls, value: Any): # noqa: pydantic example, this is run before model is constructed
        if isinstance(value, str):
            return Path(value)
        return value
