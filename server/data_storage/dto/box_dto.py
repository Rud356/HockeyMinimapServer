from pydantic import BaseModel

from server.data_storage.dto.relative_point_dto import RelativePointDTO


class BoxDTO(BaseModel):
    top_point: RelativePointDTO
    bottom_point: RelativePointDTO
