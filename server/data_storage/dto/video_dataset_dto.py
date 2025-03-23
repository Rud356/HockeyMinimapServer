from pydantic import BaseModel

from server.data_storage.sql_implementation.tables.teams_subset import TeamsSubset


class VideoDatasetDTO(BaseModel):
    video_id: int
    dataset_id: int
    subsets: TeamsSubset
