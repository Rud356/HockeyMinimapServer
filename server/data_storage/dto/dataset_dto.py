from pydantic import BaseModel

from server.data_storage.dto.teams_subset_dto import TeamsSubsetDTO


class DatasetDTO(BaseModel):
    dataset_id: int
    video_id: int

    subsets: list[TeamsSubsetDTO]
