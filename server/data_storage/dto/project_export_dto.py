from pydantic import BaseModel

from server.data_storage.dto.dataset_dto import DatasetDTO
from server.data_storage.dto.frame_data_dto import FrameDataDTO
from server.data_storage.dto.minimap_data_dto import MinimapDataDTO
from server.data_storage.dto.project_dto import ProjectDTO
from server.data_storage.dto.video_dto import VideoDTO


class ProjectExportDTO(BaseModel):
    project_header: ProjectDTO
    video_data: VideoDTO
    minimap_data: list[MinimapDataDTO]
    frame_data: FrameDataDTO
    teams_dataset: DatasetDTO
