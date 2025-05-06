from pydantic import BaseModel

from server.data_storage.dto.relative_point_dto import RelativePointDTO


class PointsMapping(BaseModel):
    map_point: RelativePointDTO
    video_point: RelativePointDTO
