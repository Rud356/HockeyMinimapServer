from pydantic import BaseModel

from server.data_storage.dto.subset_data_dto import SubsetDataDTO


class TeamsSubsetDTO(BaseModel):
    subset_id: int
    from_frame_id: int
    to_frame_id: int

    subset_data: list[SubsetDataDTO]
