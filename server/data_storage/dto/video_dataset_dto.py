from pydantic import BaseModel

from server.data_storage.dto import TeamsSubsetDTO


class VideoDatasetDTO(BaseModel):
    video_id: int
    dataset_id: int
    subsets: TeamsSubsetDTO
