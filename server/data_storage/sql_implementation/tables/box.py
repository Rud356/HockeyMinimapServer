from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from server.data_storage.sql_implementation.tables.base import Base

if TYPE_CHECKING:
    from server.data_storage.sql_implementation.tables.point import Point


class Box(Base):
    """
    Представляет данные о прямоугольниках.
    """
    box_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    top_point_id: Mapped[int] = mapped_column(ForeignKey("point.point_id"))
    bottom_point_id: Mapped[int] = mapped_column(ForeignKey("point.point_id"))

    top_point: Mapped["Point"] = relationship(
        primaryjoin="Box.top_point_id == Point.point_id",
        lazy="joined",
        cascade="all, delete"
    )
    bottom_point: Mapped["Point"] = relationship(
        primaryjoin="Box.bottom_point_id == Point.point_id",
        lazy="joined",
        cascade="all, delete"
    )

    __tablename__ = "box"
