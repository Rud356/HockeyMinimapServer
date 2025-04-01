from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from server.data_storage.sql_implementation.tables.base import Base

if TYPE_CHECKING:
    from .user import User


class UserPermissions(Base):
    """
    Описывает таблицу прав пользователей сервера.
    """
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)

    can_administrate_users: Mapped[bool]
    can_create_projects: Mapped[bool]

    user: Mapped["User"] = relationship(
        back_populates="user_permissions",
        lazy="joined"
    )

    __tablename__ = "user_permissions"
