from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm import mapped_column

from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.data_storage.sql_implementation.tables.base import Base

if TYPE_CHECKING:
    from server.data_storage.sql_implementation.tables.box import Box
    from server.data_storage.sql_implementation.tables.team_assignment import TeamAssignment
    from server.data_storage.sql_implementation.tables.player import Player
    from server.data_storage.sql_implementation.tables.point import Point


class PlayerData(Base):
    """
    Описывает данные отслеживания игрока.
    """
    tracking_id: Mapped[int] = mapped_column(
        primary_key=True
    )
    video_id: Mapped[int] = mapped_column(
        primary_key=True
    )
    frame_id: Mapped[int] = mapped_column(
        primary_key=True
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.player_id")
    )

    player_on_camera_box_id: Mapped[int] = mapped_column(
        ForeignKey("box.box_id")
    )
    point_on_minimap_id: Mapped[int] = mapped_column(
        ForeignKey("point.point_id")
    )
    class_id: Mapped[PlayerClasses]

    box: Mapped["Box"] = relationship(
        lazy="joined"
    )
    player: Mapped["Player"] = relationship(
        lazy="joined"
    )
    team: Mapped["TeamAssignment"] = relationship(
        lazy="joined"
    )
    point_on_minimap: Mapped["Point"] = relationship(
        lazy="joined"
    )

    __tablename__ = "player_data"
