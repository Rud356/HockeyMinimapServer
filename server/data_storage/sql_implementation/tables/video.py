from typing import Any, Optional, TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ColumnCollectionConstraint

from server.algorithms.enums.camera_position import CameraPosition
from server.data_storage.sql_implementation.tables.base import Base

if TYPE_CHECKING:
    from server.data_storage.sql_implementation.tables.team_dataset import TeamsDataset

class Video(Base):
    """
    Описывает таблицу видео.
    """
    video_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    fps: Mapped[float] = mapped_column(default=25.0)
    corrective_coefficient_k1: Mapped[float] = mapped_column(
        default=0.0
    )
    corrective_coefficient_k2: Mapped[float] = mapped_column(
        default=0.0
    )
    camera_position: Mapped[CameraPosition] = mapped_column(default=CameraPosition.top_left_corner)
    is_converted: Mapped[bool] = mapped_column(default=False)
    is_processed: Mapped[bool] = mapped_column(default=False)
    source_video_path: Mapped[str] = mapped_column(String, unique=True)
    converted_video_path: Mapped[Optional[str]] = mapped_column(String, unique=True)
    dataset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams_dataset.dataset_id"))

    dataset: Mapped["TeamsDataset"] = relationship(
        lazy="joined",
        primaryjoin=(
            "TeamsDataset.dataset_id == Video.dataset_id"
        )
    )

    __tablename__ = "video"
    __table_args__: tuple[ColumnCollectionConstraint | dict[Any, Any], ...] = (
        CheckConstraint("corrective_coefficient_k1 BETWEEN -1.0 AND 1.0"),
        CheckConstraint("corrective_coefficient_k2 BETWEEN -1.0 AND 1.0"),
        {}
    )
