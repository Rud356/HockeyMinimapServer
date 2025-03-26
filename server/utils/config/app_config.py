from pydantic import BaseModel, Field

from server.utils.config.minimap_config import MinimapKeyPointConfig
from server.utils.config.neural_netwroks_config import NeuralNetworkConfig
from server.utils.config.server_config import ServerSettings
from server.utils.config.video_preprocessing_config import VideoPreprocessingConfig


class AppConfig(BaseModel):
    """
    Хранит конфигурацию приложения.
    """
    debug_visualization: bool
    db_connection_string: str
    enable_gzip_compression: bool

    players_data_extraction_workers: int = Field(ge=1, lt=20)
    minimap_rendering_workers: int = Field(ge=1, lt=64)

    nn_config: NeuralNetworkConfig
    server_settings: ServerSettings
    video_processing: VideoPreprocessingConfig
    minimap_config: MinimapKeyPointConfig
