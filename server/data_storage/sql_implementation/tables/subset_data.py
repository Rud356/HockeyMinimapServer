from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql.schema import ColumnCollectionConstraint

from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.enums.team import Team
from server.data_storage.sql_implementation.tables.base import Base

if TYPE_CHECKING:
    from server.data_storage.sql_implementation.tables.box import Box
    from server.data_storage.sql_implementation.tables.teams_subset import TeamsSubset


class SubsetData(Base):
    """
    Описывает данные с конкретного кадра с примером команды.
    """
    tracking_id: Mapped[int] = mapped_column(
        primary_key=True
    )
    subset_id: Mapped[int] = mapped_column(
        ForeignKey("teams_subset.subset_id"),
        primary_key=True
    )
    video_id: Mapped[int] = mapped_column(
        primary_key=True
    )
    frame_id: Mapped[int] = mapped_column(
        primary_key=True
    )
    team_id: Mapped[Optional[Team]]
    box_id: Mapped[int] = mapped_column(
        ForeignKey("box.box_id")
    )
    class_id: Mapped[PlayerClasses]

    box: Mapped["Box"] = relationship(
        lazy="joined"
    )
    subset: Mapped["TeamsSubset"] = relationship(
        back_populates="subset_data",
        lazy="joined"
    )

    __table_args__: tuple[ColumnCollectionConstraint | dict[Any, Any], ...] = (
        ForeignKeyConstraint(
            ["video_id", "frame_id"], ["frame.video_id", "frame.frame_id"]
        ),
        {}
    )
    __tablename__ = "subset_data"
