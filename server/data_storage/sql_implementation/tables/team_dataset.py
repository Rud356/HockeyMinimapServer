from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from server.data_storage.sql_implementation.tables.base import Base


class TeamsDataset(Base):
    """
    Описывает таблицу дата сетов разделения команд.
    """
    dataset_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("video.video_id"), index=True)

    __tablename__ = "teams_dataset"
