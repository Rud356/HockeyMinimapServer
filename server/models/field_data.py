from typing import TYPE_CHECKING

from server.models.coordinates import Coordinates
from server.models.minimap import MiniMap

if TYPE_CHECKING:
    from server.models.frame import Frame


class FieldData:
    video_id: int
    frame_id: int
    minimap: MiniMap
    key_points_data: list[Coordinates]

    @classmethod
    async def generate_field_data(cls, frame: Frame) -> "FieldData":
        ...

    def translate_to_minimap_coordinates(self) -> Coordinates:
        ...

    async def save_field_data(self) -> bool:
        ...
