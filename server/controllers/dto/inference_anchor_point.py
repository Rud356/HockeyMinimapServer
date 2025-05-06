from typing import Optional

from pydantic import BaseModel, Field

from server.data_storage.dto.relative_point_dto import RelativePointDTO


class InferenceAnchorPoint(BaseModel):
    anchor_point: Optional[RelativePointDTO] = Field(
        default=None,
        description="Якорная точка, считаемая центральной для поля в "
                    "рамках вычислений относительных положений других точек"
    )
