from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql.schema import CheckConstraint, ColumnCollectionConstraint

from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.data_storage.dto import BoxDTO, PointDTO
from server.data_storage.dto.relative_point_dto import RelativePointDTO
from server.data_storage.sql_implementation.tables.base import Base
from server.data_storage.sql_implementation.tables.team_assignment import TeamAssignment

if TYPE_CHECKING:
    from server.data_storage.sql_implementation.tables.player import Player


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
    class_id: Mapped[PlayerClasses]

    player_on_camera_top_x: Mapped[float] = mapped_column(
        CheckConstraint("player_on_camera_top_x BETWEEN 0.0 AND 1.0")
    )
    player_on_camera_top_y: Mapped[float] = mapped_column(
        CheckConstraint("player_on_camera_top_y BETWEEN 0.0 AND 1.0")
    )
    player_on_camera_bottom_x: Mapped[float] = mapped_column(
        CheckConstraint("player_on_camera_bottom_x BETWEEN 0.0 AND 1.0")
    )
    player_on_camera_bottom_y: Mapped[float] = mapped_column(
        CheckConstraint("player_on_camera_bottom_y BETWEEN 0.0 AND 1.0")
    )
    point_on_minimap_x: Mapped[float] = mapped_column(
        CheckConstraint("point_on_minimap_x BETWEEN 0.0 AND 1.0")
    )
    point_on_minimap_y: Mapped[float] = mapped_column(
        CheckConstraint("point_on_minimap_y BETWEEN 0.0 AND 1.0")
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

    __tablename__ = "player_data"
    __table_args__: tuple[ColumnCollectionConstraint | dict[Any, Any], ...] = (
        ForeignKeyConstraint(
            ["video_id", "frame_id"], ["frame.video_id", "frame.frame_id"]
        ),
        {}
    )

    @property
    def box(self) -> BoxDTO:
        """
        Получает представление позиций точек в виде охватывающего прямоугольника.

        :return: Охватывающий прямоугольник.
        """
        return BoxDTO(
            top_point=RelativePointDTO(
                x=self.player_on_camera_top_x,
                y=self.player_on_camera_top_y
            ),
            bottom_point=RelativePointDTO(
                x=self.player_on_camera_bottom_x,
                y=self.player_on_camera_bottom_y
            )
        )

    @property
    def point_on_minimap(self) -> RelativePointDTO:
        """
        Получает представление позиции игрока на карте.

        :return: Точка позиции на карте.
        """
        return RelativePointDTO(
            x=self.point_on_minimap_x,
            y=self.point_on_minimap_y
        )
