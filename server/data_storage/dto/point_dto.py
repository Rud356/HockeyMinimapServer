from typing import ClassVar
from pydantic import BaseModel, ConfigDict


class PointDTO(BaseModel):
    x: float
    y: float

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True) # noqa: overriding defaults to have it hashable
