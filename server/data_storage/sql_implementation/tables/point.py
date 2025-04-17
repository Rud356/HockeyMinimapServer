from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from server.data_storage.sql_implementation.tables.base import Base


class Point(Base):
    """
    Представляет данные о точках в относительных координатах.
    """
    point_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    x: Mapped[float] = mapped_column(CheckConstraint("x BETWEEN 0.0 AND 1.0"))
    y: Mapped[float] = mapped_column(CheckConstraint("x BETWEEN 0.0 AND 1.0"))

    __tablename__ = "point"

