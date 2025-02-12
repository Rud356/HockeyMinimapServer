from pydantic import BaseModel

from server.utils.config.neural_netwroks_config import NeuralNetworkConfig
from server.utils.config.server_config import ServerConfig
from server.utils.config.video_preprocessing_config import VideoPreprocessingConfig


class AppConfig(BaseModel):
    """
    Хранит конфигурацию приложения.
    """
    debug_visualization: bool
    db_connection_string: str

    nn_config: NeuralNetworkConfig
    server_settings: ServerConfig
    video_processing: VideoPreprocessingConfig
