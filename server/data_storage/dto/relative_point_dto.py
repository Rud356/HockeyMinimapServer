from typing import ClassVar

from pydantic import ConfigDict, Field

from server.data_storage.dto.point_dto import PointDTO


class RelativePointDTO(PointDTO):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True
    ) # noqa: overriding defaults to have it hashable
