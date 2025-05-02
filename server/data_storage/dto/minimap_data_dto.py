from pydantic import BaseModel

from server.data_storage.dto.relative_point_dto import RelativePointDTO


class MinimapDataDTO(BaseModel):
    map_data_id: int
    point_on_camera: RelativePointDTO
    point_on_minimap: RelativePointDTO
    is_used: bool
