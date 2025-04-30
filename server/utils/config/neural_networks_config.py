from typing import Any, Optional
from pathlib import Path

from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError


class NeuralNetworkConfig(BaseModel):
    """
    Конфигурация запуска нейронных сетей.
    """
    field_detection_model_path: Path
    player_detection_model_path: Path

    device: Optional[str] = None
    max_batch_size: int = Field(ge=1, lt=50)

    @field_validator('field_detection_model_path', 'player_detection_model_path', mode='after')
    @classmethod
    def check_is_path_to_directory(cls, v: Any) -> Path:
        if isinstance(v, Path) and v.is_file():
            return v

        else:
            raise PydanticCustomError(
                'path_validation_error',
                '{path} not a valid path to a neural network weights!',
                {'path': v},
            )
