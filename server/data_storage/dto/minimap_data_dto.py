from pydantic import BaseModel

from server.data_storage.dto.point_dto import PointDTO


class MinimapDataDTO(BaseModel):
    map_data_id: int
    point_on_camera: PointDTO
    point_on_minimap: PointDTO
