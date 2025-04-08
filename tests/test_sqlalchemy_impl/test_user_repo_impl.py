from sqlalchemy import Select

from server.data_storage.sql_implementation.tables import User
from .fixtures import *

async def test_db_init(repo):
    await repo.transaction.session.execute(
        Select(User)
    )

