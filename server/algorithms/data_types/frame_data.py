from dataclasses import dataclass

from server.algorithms.data_types.player_data import PlayerData


@dataclass(frozen=True)
class FrameData:
    """
    Описывает данные о конкретном кадре.
    """
    frame_id: int
    player_data_on_frame: list[PlayerData]
