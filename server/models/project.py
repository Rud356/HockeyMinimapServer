from server.algorithms.field_detection import FieldDetection
from server.algorithms.player_tracking import PlayerTracker
from server.data_storage.repository import Repository
from server.models.user import User
from server.models.video import Video


class Project:
    project_id: int
    project_name: str
    video_id: int
    team_names: dict[int, str]
    tracking_algorithm: PlayerTracker
    field_detection_algorithm: FieldDetection
    data_repository: Repository

    @classmethod
    async def create_project(
        cls, author: User, name: str,
        video_id: int, data_repository: Repository
    ) -> "Project":
        ...

    @classmethod
    async def load_project(
        cls, by_id: int, data_repository: Repository
    ) -> "Project":
        ...

    @classmethod
    async def import_project(
        cls, author: User, name: str, video_id: int, data_repository: Repository
    ) -> "Project":
        ...

    async def set_camera_position(self, position: int) -> bool:
        ...

    async def set_team_name(self, team_id: int, team_name: str) -> bool:
        ...

    async def save_project_state(self) -> None:
        ...

    async def get_projects_video(self) -> Video:
        ...
