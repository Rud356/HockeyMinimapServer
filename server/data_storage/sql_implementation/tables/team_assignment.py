from typing import Optional

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from server.algorithms.enums.team import Team
from server.data_storage.sql_implementation.tables.base import Base


class TeamAssignment(Base):
    """
    Описывает таблицу назначения команд для отслеживаний игроков.
    """
    tracking_id: Mapped[int] = mapped_column(
        ForeignKey("player_data.tracking_id"),
        primary_key=True
    )
    video_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("player_data.video_id"),
        primary_key=True
    )
    frame_id: Mapped[int] = mapped_column(
        ForeignKey("player_data.frame_id")
    )
    team_id: Mapped[Optional[Team]] = mapped_column(default=None)

    __tablename__ = "team_assignment"
