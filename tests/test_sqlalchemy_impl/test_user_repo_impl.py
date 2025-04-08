from sqlalchemy import Select

from server.data_storage.sql_implementation.tables import User
from .fixtures import *

async def test_db_init(repo):
    async with repo.transaction as tr:
        await tr.session.execute(
            Select(User)
        )

