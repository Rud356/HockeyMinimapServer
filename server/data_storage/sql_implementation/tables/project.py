import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from server.data_storage.sql_implementation.tables.base import Base


class Project(Base):
    """
    Описывает таблицу, хранящую проекты.
    """
    project_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    for_video_id: Mapped[int] = mapped_column(ForeignKey("video.video_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    team_home_name: Mapped[str] = mapped_column(String(30), default="Home")
    team_away_name: Mapped[str] = mapped_column(String(30), default="Away")

    __tablename__ = "project"
