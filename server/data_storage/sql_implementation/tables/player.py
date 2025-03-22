from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from server.data_storage.sql_implementation.tables.base import Base


class Player(Base):
    """
    Описывает таблицу пользовательских назначений идентификаторов
    """
    player_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("video.video_id"), index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    __tablename__ = "player"
