from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.data_storage.sql_implementation.tables.base import Base
from server.data_storage.sql_implementation.tables.player_data import PlayerData
from server.data_storage.sql_implementation.tables.subset_data import SubsetData


class Frame(Base):
    """
    Представляет данные одного кадра видео.
    """
    frame_id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("video.video_id"), primary_key=True)

    player_data: Mapped[list[PlayerData]] = relationship(
        primaryjoin="and_(PlayerData.video_id == Frame.video_id, PlayerData.frame_id == Frame.frame_id)",
        lazy="raise"
    )
    subset_data: Mapped[list[SubsetData]] = relationship(
        primaryjoin="and_(SubsetData.video_id == Frame.video_id, SubsetData.frame_id == Frame.frame_id)",
        lazy="raise"
    )

    __tablename__ = "frame"
