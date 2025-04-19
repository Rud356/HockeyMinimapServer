from typing import Any, Optional

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql.schema import ColumnCollectionConstraint, ForeignKeyConstraint

from server.algorithms.enums.team import Team
from server.data_storage.sql_implementation.tables.base import Base


class TeamAssignment(Base):
    """
    Описывает таблицу назначения команд для отслеживаний игроков.
    """
    tracking_id: Mapped[int] = mapped_column(
        primary_key=True
    )
    video_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )
    frame_id: Mapped[int] = mapped_column()
    team_id: Mapped[Optional[Team]] = mapped_column(default=None)

    __tablename__ = "team_assignment"
    __table_args__: tuple[ColumnCollectionConstraint | dict[Any, Any], ...] = (
        ForeignKeyConstraint(
            ["video_id", "tracking_id", "frame_id"],
            ["player_data.video_id", "player_data.tracking_id", "player_data.frame_id"]
        ),
        {}
    )
