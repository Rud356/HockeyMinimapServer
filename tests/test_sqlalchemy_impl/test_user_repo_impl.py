import pytest
from sqlalchemy import Select

from server.data_storage.dto import UserDTO, UserPermissionsDTO, UserPermissionsData
from server.data_storage.exceptions import DataIntegrityError, NotFoundError
from server.data_storage.sql_implementation.tables import User
from .fixtures import *


async def test_db_init(repo):
    async with repo.transaction as tr:
        await tr.session.execute(
            Select(User)
        )


async def test_user_creation(repo):
    async with repo.transaction as tr:
        await repo.user_repo.create_user(
            username="UserTest1",
            display_name="User test 1",
            password="Hard password",
            user_permissions=UserPermissionsData(
                can_administrate_users=True,
                can_create_projects=True
            )
        )

        await tr.commit()

    async with repo.transaction as tr:
        result = await tr.session.execute(
            Select(User)
        )
        user_data: User = result.scalars().one()

    assert user_data.username == "UserTest1", "Must have same user since it is only one in db"


async def test_user_creation_with_invalid_data(repo):
    with pytest.raises(DataIntegrityError):
        async with repo.transaction as tr:
            await repo.user_repo.create_user(
                username="UserTest1",
                display_name="User test 1",
                password=[*"Hard password"], # noqa: testing for invalid data type
                user_permissions=UserPermissionsData(
                    can_administrate_users=True,
                    can_create_projects=True
                )
            )

            await tr.commit()

    with pytest.raises(DataIntegrityError):
        async with repo.transaction as tr:
            await repo.user_repo.create_user(
                username=100.7, # noqa: testing for invalid data type
                display_name="User test 1",
                password="Hard password",
                user_permissions=UserPermissionsData(
                    can_administrate_users=True,
                    can_create_projects=True
                )
            )

            await tr.commit()


async def test_user_creation_with_duplicate_username(repo):
    async with repo.transaction as tr:
        await repo.user_repo.create_user(
            username="UserTest1",
            display_name="User test 1",
            password="Hard password",
            user_permissions=UserPermissionsData(
                can_administrate_users=True,
                can_create_projects=True
            )
        )

        with pytest.raises(DataIntegrityError):
            await repo.user_repo.create_user(
                username="UserTest1",
                display_name="User test 1",
                password="Hard password",
                user_permissions=UserPermissionsData(
                    can_administrate_users=True,
                    can_create_projects=True
                )
            )
            await tr.commit()


async def test_user_fetching(repo):
    user_data: UserDTO = UserDTO(
        user_id=1,
        username="UserTest1",
        display_name="User test 1",
        user_permissions=UserPermissionsDTO(
            can_administrate_users=True,
            can_create_projects=True
        )
    )

    async with repo.transaction as tr:
        user_data_created = await repo.user_repo.create_user(
            username=user_data.username,
            display_name=user_data.display_name,
            password="Hard password",
            user_permissions=UserPermissionsData(
                can_administrate_users=True,
                can_create_projects=True
            )
        )
        await tr.commit()

    async with repo.transaction:
        result = await repo.user_repo.get_user(
            user_id=user_data_created.user_id
        )

    assert result == user_data_created, "Unexpected difference in data"


async def test_user_fetching_with_non_existing_id(repo):
    # No users were created, so it is passes by raising exception
    with pytest.raises(NotFoundError):
        async with repo.transaction:
            await repo.user_repo.get_user(
                user_id=1000
            )


async def test_user_fetching_with_invalid_type(repo):
    # No users were created, so it is passes by raising exception
    with pytest.raises(NotFoundError):
        async with repo.transaction:
            await repo.user_repo.get_user(
                user_id='1000' # noqa: testing different data types
            )

    with pytest.raises(ValueError):
        async with repo.transaction:
            await repo.user_repo.get_user(
                user_id=[*'1000'] # noqa: testing different data types
            )


async def test_users_batch_select(repo):
    user_ref: list[UserDTO] = []

    async with repo.transaction as tr:
        for i in range(100):
            user_data = await repo.user_repo.create_user(
                username=f"UserTest{i}",
                display_name=f"User test {i}",
                password=f"Hard password {i}",
                user_permissions=UserPermissionsData(
                    can_administrate_users=True,
                    can_create_projects=True
                )
            )
            user_ref.append(user_data)

        await tr.commit()

    async with repo.transaction as tr:
        users_compare: list[UserDTO] = await repo.user_repo.get_users()

    assert users_compare == user_ref

    async with repo.transaction as tr:
        users_compare: list[UserDTO] = await repo.user_repo.get_users(limit=10)

    assert users_compare == user_ref[:10]

    async with repo.transaction as tr:
        users_compare: list[UserDTO] = await repo.user_repo.get_users(limit=10, offset=10)

    assert users_compare == user_ref[10:20]


async def test_deleting_user(repo):
    async with repo.transaction as tr:
        user_data: UserDTO = await repo.user_repo.create_user(
            username="UserTest1",
            display_name="User test 1",
            password="Hard password",
            user_permissions=UserPermissionsData(
                can_administrate_users=True,
                can_create_projects=True
            )
        )

        await tr.commit()

    async with repo.transaction as tr:
        has_been_deleted: bool = await repo.user_repo.delete_user(user_data.user_id)
        assert has_been_deleted, "Expected to delete user in this transaction"


async def test_deleting_non_existent_user(repo):
    async with repo.transaction as tr:
        has_been_deleted: bool = await repo.user_repo.delete_user(1000)
        assert not has_been_deleted, "Expected to delete user in this transaction"


async def test_changing_user_permissions(repo):
    updated_permissions = UserPermissionsData(
        can_administrate_users=False,
        can_create_projects=False
    )
    updated_permissions_expected = UserPermissionsDTO(
        can_administrate_users=False,
        can_create_projects=False
    )

    async with repo.transaction as tr:
        user_data: UserDTO = await repo.user_repo.create_user(
            username="UserTest1",
            display_name="User test 1",
            password="Hard password",
            user_permissions=UserPermissionsData(
                can_administrate_users=True,
                can_create_projects=True
            )
        )

        await tr.commit()

    async with repo.transaction as tr:
        got_permissions_back = await repo.user_repo.change_user_permissions(
            user_id=1, new_permissions=updated_permissions
        )

    async with repo.transaction as tr:
        fetched_data = await repo.user_repo.get_user(user_id=1)

    assert got_permissions_back == updated_permissions_expected, ("Unexpected return value from change permissions "
                                                                  "method")
    assert fetched_data.user_permissions == updated_permissions_expected, "Unexpected fetched permissions"


async def test_user_authentication(repo):
    async with repo.transaction as tr:
        user_data: UserDTO = await repo.user_repo.create_user(
            username="UserTest1",
            display_name="User test 1",
            password="Hard password",
            user_permissions=UserPermissionsData(
                can_administrate_users=True,
                can_create_projects=True
            )
        )

        await tr.commit()

    async with repo.transaction as tr:
        fetched_user: UserDTO = await repo.user_repo.authenticate_user(user_data.username, "Hard password")

    assert fetched_user == user_data, "User data mismatch"


async def test_user_authentication_failure(repo):
    async with repo.transaction as tr:
        user_data: UserDTO = await repo.user_repo.create_user(
            username="UserTest1",
            display_name="User test 1",
            password="Hard password",
            user_permissions=UserPermissionsData(
                can_administrate_users=True,
                can_create_projects=True
            )
        )

        await tr.commit()

    with pytest.raises(ValueError):
        async with repo.transaction as tr:
            await repo.user_repo.authenticate_user(user_data.username, "")


async def test_edit_user(repo):
    async with repo.transaction as tr:
        user_data: UserDTO = await repo.user_repo.create_user(
            username="UserTest1",
            display_name="User test 1",
            password="Hard password",
            user_permissions=UserPermissionsData(
                can_administrate_users=True,
                can_create_projects=True
            )
        )
        await tr.commit()

    async with repo.transaction as tr:
        fetched_user: UserDTO = await repo.user_repo.edit_user(
            user_data.user_id, "Hello world"
        )

    assert fetched_user.username == "Hello world", "User data mismatch"

    async with repo.transaction as tr:
        fetched_user: UserDTO = await repo.user_repo.edit_user(
            user_data.user_id, display_name="New name"
        )

    assert fetched_user.display_name == "New name", "User data mismatch"

    async with repo.transaction as tr:
        fetched_user: UserDTO = await repo.user_repo.edit_user(
            user_data.user_id, password="Hello world!!!"
        )

    async with repo.transaction as tr:
        fetched_user: UserDTO = await repo.user_repo.authenticate_user("Hello world", "Hello world!!!")
        assert fetched_user.user_id == user_data.user_id, "User password wasn't changed properly"
