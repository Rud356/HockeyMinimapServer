from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql.schema import ColumnCollectionConstraint

from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.data_storage.sql_implementation.tables.base import Base
from server.data_storage.sql_implementation.tables.team_assignment import TeamAssignment

if TYPE_CHECKING:
    from server.data_storage.sql_implementation.tables.box import Box
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
    player_id: Mapped[Optional[int]] = mapped_column(
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
    player: Mapped[Optional["Player"]] = relationship(
        lazy="joined"
    )
    team: Mapped[Optional["TeamAssignment"]] = relationship(
        primaryjoin="and_("
                    "TeamAssignment.tracking_id == PlayerData.tracking_id, "
                    "TeamAssignment.video_id == PlayerData.video_id, "
                    "TeamAssignment.team_id.isnot(None)"
                    ")",
        lazy="joined"
    )
    point_on_minimap: Mapped["Point"] = relationship(
        lazy="joined"
    )

    __tablename__ = "player_data"
    __table_args__: tuple[ColumnCollectionConstraint | dict[Any, Any], ...] = (
        ForeignKeyConstraint(
            ["video_id", "frame_id"], ["frame.video_id", "frame.frame_id"]
        ),
        {}
    )

