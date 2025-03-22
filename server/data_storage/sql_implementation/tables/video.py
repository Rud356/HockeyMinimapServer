from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from server.algorithms.enums.camera_position import CameraPosition
from server.data_storage.sql_implementation.tables.base import Base

if TYPE_CHECKING:
    from server.data_storage.sql_implementation.tables.team_dataset import TeamsDataset

class Video(Base):
    """
    Описывает таблицу видео.
    """
    video_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    corrective_coefficient_k1: Mapped[float] = mapped_column(default=0.0)
    corrective_coefficient_k2: Mapped[float] = mapped_column(default=0.0)
    camera_position: Mapped[CameraPosition]
    is_converted: Mapped[bool] = mapped_column(default=False)
    is_processed: Mapped[bool] = mapped_column(default=False)
    source_video_path: Mapped[str] = mapped_column(String, unique=True)
    converted_video_path: Mapped[str] = mapped_column(String, unique=True)
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("dataset.dataset_id"))

    dataset: Mapped["TeamsDataset"] = relationship(
        lazy="joined"
    )

    __tablename__ = "video"
