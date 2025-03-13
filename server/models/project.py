from typing import Optional, TYPE_CHECKING

from server.models.video import Video

if TYPE_CHECKING:
    from server.algorithms.field_detection import FieldDetection
    from server.algorithms.player_tracking_test import PlayerTracker
    from server.models.user import User
    from server.data_storage.repository import Repository


class Project:
    project_id: int
    project_name: str
    video_id: int
    team_names: dict[int, str]
    tracking_algorithm: PlayerTracker
    field_detection_algorithm: FieldDetection
    data_repository: Repository

    def __init__(
        self,
        project_id: int,
        project_name: str,
        video_id: int,
        tracking_algorithm: PlayerTracker,
        field_detection_algorithm: FieldDetection,
        team_names: Optional[dict[int, str]] = None,
    ):
        self.project_id = project_id
        self.project_name = project_name
        self.video_id = video_id
        self.team_names = team_names or {0: "Команда 1", 1: "Команда 2"}
        self.tracking_algorithm = tracking_algorithm
        self.field_detection_algorithm = field_detection_algorithm

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
        cls, author: User, name: str, video_id: int,
        data_repository: Repository
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
