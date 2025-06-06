from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from server.algorithms.enums import Team
from server.data_storage.sql_implementation.tables.base import Base


class Player(Base):
    """
    Описывает таблицу пользовательских назначений идентификаторов.
    """
    player_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="Идентификатор записи пользовательского имени."
    )
    video_id: Mapped[int] = mapped_column(ForeignKey("video.video_id"), index=True)
    user_id: Mapped[Optional[str]] = mapped_column(
        String, nullable=True, comment="Пользовательское имя игрока."
    )
    team_id: Mapped[Optional[Team]] = mapped_column(default=None, comment="Команда игрока.")

    __tablename__ = "player"
    __table_args__ = {"sqlite_autoincrement": True}
