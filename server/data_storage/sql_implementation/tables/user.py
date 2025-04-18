from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from server.data_storage.sql_implementation.tables.base import Base

if TYPE_CHECKING:
    from .user_permissions import UserPermissions


class User(Base):
    """
    Описывает таблицу пользователей сервера.
    """
    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    display_name: Mapped[str] = mapped_column(
        String(255)
    )
    password_hash: Mapped[str] = mapped_column(
        String(64)
    )

    user_permissions: Mapped["UserPermissions"] = relationship(
        back_populates="user",
        lazy="joined",
        cascade="all, delete-orphan"
    )

    __tablename__ = "users"
