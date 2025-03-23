from pydantic import BaseModel

from server.data_storage.dto.player_data_dto import PlayerDataDTO


class FrameDataDTO(BaseModel):
    from_frame: int
    to_frame: int
    frames: list[list[PlayerDataDTO]]
