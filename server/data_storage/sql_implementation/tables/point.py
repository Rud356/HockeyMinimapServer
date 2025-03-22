from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from server.data_storage.sql_implementation.tables.base import Base


class Point(Base):
    """
    Представляет данные о точках.
    """
    point_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    x: Mapped[float]
    y: Mapped[float]

    __tablename__ = "point"
