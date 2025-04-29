from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

from server.utils.config.minimap_config import MinimapKeyPointConfig
from server.utils.config.neural_networks_config import NeuralNetworkConfig
from server.utils.config.server_config import ServerSettings
from server.utils.config.video_preprocessing_config import VideoPreprocessingConfig


class AppConfig(BaseModel):
    """
    Хранит конфигурацию приложения.
    """
    local_mode: bool
    debug_visualization: bool
    db_connection_string: str
    enable_gzip_compression: bool
    server_jwt_key: str

    static_path: Path
    players_data_extraction_workers: int = Field(ge=1, lt=20)
    minimap_frame_buffer: int = Field(ge=1, lt=120)
    prefetch_frame_buffer: int = Field(ge=1)
    minimap_rendering_workers: int = Field(ge=1, lt=64)
    video_processing_workers: int = Field(ge=1, lt=64)

    nn_config: NeuralNetworkConfig
    server_settings: ServerSettings
    video_processing: VideoPreprocessingConfig
    minimap_config: MinimapKeyPointConfig

    @field_validator('static_path', mode='before')
    @classmethod
    def check_is_path_to_directory(cls, v: Any) -> Path:
        if isinstance(v, Path) and v.is_dir():
            return v

        elif isinstance(v, str) and (path := Path(v)).is_dir():
            return path

        else:
            raise PydanticCustomError(
                'path_validation_error',
                '{path} not a valid path to directory!',
                {'path': v},
            )
