from typing import Optional
from pathlib import Path

from pydantic import BaseModel, Field


class NeuralNetworkConfig(BaseModel):
    """
    Конфигурация запуска нейронных сетей.
    """
    field_detection_model_path: Path
    player_detection_model_path: Path

    device: Optional[str] = None
    max_batch_size: int = Field(ge=1, lt=50)
