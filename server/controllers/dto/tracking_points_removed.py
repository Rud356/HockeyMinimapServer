from pydantic import BaseModel, Field


class TrackingPointsRemoved(BaseModel):
    points_removed: int = Field(description="Сколько точек было удалено")
