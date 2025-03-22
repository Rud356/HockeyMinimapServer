from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from server.data_storage.sql_implementation.tables.base import Base


class Frame(Base):
    """
    Представляет данные одного кадра видео.
    """
    frame_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    video_id: Mapped[int] = mapped_column(ForeignKey("video.video_id"), primary_key=True)

    __tablename__ = "frame"
