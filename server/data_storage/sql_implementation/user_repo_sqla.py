import hashlib

from server.data_storage.dto import UserDTO
from server.data_storage.dto import UserPermissionsData
from server.data_storage.dto import UserPermissionsDTO
from server.data_storage.protocols import UserRepo
from server.data_storage.sql_implementation.tables.user import User
from server.data_storage.sql_implementation.tables.user_permissions import UserPermissions
from server.data_storage.sql_implementation.transaction_manager_sqla import TransactionManagerSQLA


class UserRepoSQLA(UserRepo):
    def __init__(self, transaction: TransactionManagerSQLA):
        self.transaction: TransactionManagerSQLA = transaction

    async def create_user(
        self, username: str,
        display_name: str,
        password: str,
        user_permissions: UserPermissionsData
    ) -> UserDTO:
        user = User(
            username=username,
            display_name=display_name,
            password_hash=hashlib.sha256(password.encode('utf8')).digest(),
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
