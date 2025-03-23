from pydantic import BaseModel

from server.data_storage.dto.point_dto import PointDTO


class BoxDTO(BaseModel):
    top_point: PointDTO
    bottom_point: PointDTO
