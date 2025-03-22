from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm import mapped_column

from server.data_storage.sql_implementation.tables.base import Base

if TYPE_CHECKING:
    from server.data_storage.sql_implementation.tables.point import Point


class MapData(Base):
    """
    Описывает таблицу соотнесения точек мини-карты и игрового поля в камере.
    """
    map_data_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("video.video_id"),
        primary_key=True
    )
    point_on_minimap_id: Mapped[int] = mapped_column(
        ForeignKey("point.point_id")
    )
    camera_point_id: Mapped[int] = mapped_column(
        ForeignKey("point.point_id")
    )
    is_used: Mapped[bool] = mapped_column(
        default=True
    )
    point_on_camera: Mapped["Point"] = relationship(
        primaryjoin="MapData.camera_point_id == Point.point_id",
        lazy="joined"
    )
    point_on_minimap: Mapped["Point"] = relationship(
        primaryjoin="MapData.point_on_minimap_id == Point.point_id",
        lazy="joined"
    )

    __tablename__ = "map_data"
