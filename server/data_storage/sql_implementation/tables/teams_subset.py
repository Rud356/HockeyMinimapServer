from typing import List, TYPE_CHECKING

from sqlalchemy import ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.orm import mapped_column

from server.data_storage.sql_implementation.tables.base import Base

if TYPE_CHECKING:
    from server.data_storage.sql_implementation.tables.subset_data import SubsetData


class TeamsSubset(Base):
    """
    Описывает подмножество основного дата сета разделения на команды.
    """
    subset_id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("teams_dataset.dataset_id")
    )
    video_id: Mapped[int] = mapped_column(
        ForeignKey("teams_dataset.video_id"),
    )
    from_frame_id: Mapped[int]
    to_frame_id: Mapped[int]

    subset_data: Mapped[List["SubsetData"]] = relationship(
        back_populates="subset",
        lazy="immediate"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["from_frame_id", "video_id"], ["frame.frame_id", "frame.video_id"]
        ),
        ForeignKeyConstraint(
            ["to_frame_id", "video_id"], ["frame.frame_id", "frame.video_id"]
        ),
        {}
    )

    __tablename__ = "teams_subset"
