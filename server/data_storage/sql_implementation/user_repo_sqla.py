import hashlib
from typing import Optional, cast

from pydantic import ValidationError
from sqlalchemy import Select
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncScalarResult

from server.data_storage.dto import UserDTO
from server.data_storage.dto import UserPermissionsDTO
from server.data_storage.dto import UserPermissionsData
from server.data_storage.exceptions import DataIntegrityError, NotFoundError
from server.data_storage.protocols import UserRepo
from server.data_storage.sql_implementation.tables.user import User
from server.data_storage.sql_implementation.tables.user_permissions import UserPermissions
from server.data_storage.sql_implementation.transaction_manager_sqla import TransactionManagerSQLA


class UserRepoSQLA(UserRepo):
    def __init__(self, transaction: TransactionManagerSQLA):
        self.transaction: TransactionManagerSQLA = transaction

    async def create_user(
        self,
        username: str,
        display_name: str,
        password: str,
        user_permissions: UserPermissionsData
    ) -> UserDTO:
        try:
            user = User(
                username=username,
                display_name=display_name,
                password_hash=hashlib.sha256(password.encode('utf8')).hexdigest(),
                user_permissions=UserPermissions(
                    can_administrate_users=user_permissions.can_administrate_users,
                    can_create_projects=user_permissions.can_create_projects
                )
            )

            nested_transaction = await self.transaction.start_nested_transaction()
            async with nested_transaction as tr:
                tr.session.add(user)
                await tr.commit()

            return UserDTO(
                user_id=user.user_id,
                username=user.username,
                display_name=user.display_name,
                user_permissions=UserPermissionsDTO(
                    can_administrate_users=user.user_permissions.can_administrate_users,
                    can_create_projects=user.user_permissions.can_create_projects
                )
            )

        except (IntegrityError, ProgrammingError, AttributeError, ValidationError) as err:
            raise DataIntegrityError("User creation had database constraints broken or data is invalid") from err

    async def get_user(self, user_id: int) -> UserDTO:
        try:
            result: Optional[User] = await self._get_user(user_id)

        except ProgrammingError:
            raise ValueError("Invalid data was provided as input")

        if result is None:
            raise NotFoundError("User with provided id was not found")

        try:
            return UserDTO(
                user_id=result.user_id,
                username=result.username,
                display_name=result.display_name,
                user_permissions=UserPermissionsDTO(
                    can_administrate_users=result.user_permissions.can_administrate_users,
                    can_create_projects=result.user_permissions.can_administrate_users
                )
            )

        except ValidationError as err:
            raise NotFoundError("Invalid data type was stored under this record") from err

    async def get_users(self, limit: int = 100, offset: int = 0) -> list[UserDTO]:
        query: Select[tuple[User, ...]] = Select(User).limit(limit).offset(offset).order_by(User.user_id)
        result: AsyncScalarResult[User] = await self.transaction.session.stream_scalars(query)
        users: list[UserDTO] = []

        async for user_record in result:
            try:
                users.append(
                    UserDTO(
                        user_id=user_record.user_id,
                        username=user_record.username,
                        display_name=user_record.display_name,
                        user_permissions=UserPermissionsDTO(
                            can_administrate_users=user_record.user_permissions.can_administrate_users,
                            can_create_projects=user_record.user_permissions.can_administrate_users
                        )
                    )
                )

            except ValidationError:
                continue

        return users

    async def delete_user(self, user_id: int) -> bool:
        async with await self.transaction.start_nested_transaction() as tr:
            result: Optional[User] = await self._get_user(user_id)

            if result is None:
                raise NotFoundError("User not found")

            await tr.session.delete(result)
            await tr.commit()
        return True

    async def change_user_permissions(self, user_id: int, new_permissions: UserPermissionsData) -> UserPermissionsDTO:
        try:
            result: Optional[User] = await self._get_user(user_id)

            if result is None:
                raise NotFoundError("User was not found with specified ID")

            async with await self.transaction.start_nested_transaction() as tr:
                result.user_permissions.can_administrate_users = bool(new_permissions.can_administrate_users)
                result.user_permissions.can_create_projects = bool(new_permissions.can_create_projects)
                await tr.commit()

        except ProgrammingError as err:
            raise ValueError("Invalid data was provided as input") from err

        return UserPermissionsDTO(
            can_administrate_users=cast(bool, result.user_permissions.can_administrate_users),
            can_create_projects=cast(bool, result.user_permissions.can_administrate_users)
        )

    async def edit_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        display_name: Optional[str] = None,
        password: Optional[str] = None
    ) -> UserDTO:
        if (username is None) and (display_name is None) and (password is None):
            raise ValueError("No data for update provided")

        try:
            result: Optional[User] = await self._get_user(user_id)

            if result is None:
                raise NotFoundError("User was not found with specified ID")

            async with await self.transaction.start_nested_transaction() as tr:
                if username:
                    result.username = username

                if display_name:
                    result.display_name = display_name

                if password:
                    result.password_hash = hashlib.sha256(password.encode('utf8')).hexdigest()\

                await tr.commit()

        except (ProgrammingError, IntegrityError) as err:
            raise ValueError("Invalid data was provided as input") from err

        return UserDTO(
                user_id=result.user_id,
                username=cast(str, result.username),
                display_name=cast(str, result.display_name),
                user_permissions=UserPermissionsDTO(
                    can_administrate_users=result.user_permissions.can_administrate_users,
                    can_create_projects=result.user_permissions.can_administrate_users
                )
            )

    async def authenticate_user(self, username: str, password: str) -> UserDTO:
        try:
            result: Optional[User] = (await self.transaction.session.execute(
                Select(User).where(User.username == username)
            )).scalar_one_or_none()

            if result is None:
                raise ValueError("User not found in database")

            if result.password_hash == hashlib.sha256(password.encode('utf8')).hexdigest():
                return UserDTO(
                    user_id=result.user_id,
                    username=result.username,
                    display_name=result.display_name,
                    user_permissions=UserPermissionsDTO(
                        can_administrate_users=result.user_permissions.can_administrate_users,
                        can_create_projects=result.user_permissions.can_administrate_users
                    )
                )

            else:
                raise ValueError("Invalid user password")

        except ProgrammingError as err:
            raise ValueError("Invalid input data") from err

    async def _get_user(self, user_id: int) -> Optional[User]:
        """
        Получает объект записи о пользователе.

        :param user_id: Идентификатор пользователя.
        :return: Запись пользователя или ничего.
        """
        result: Optional[User] = (await self.transaction.session.execute(
            Select(User).where(User.user_id == user_id)
        )).scalar_one_or_none()

        return result
