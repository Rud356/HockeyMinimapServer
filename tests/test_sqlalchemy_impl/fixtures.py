import pytest
import pytest_asyncio  # noqa: used as plugin
from dishka import Container, make_container
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from server.data_storage.sql_implementation.repository_sqla import RepositorySQLA, Repository
from server.data_storage.sql_implementation.sqla_provider import SQLAlchemyProvider


@pytest.fixture()
async def engine() -> AsyncEngine:
    engine: AsyncEngine = create_async_engine(
        "sqlite+aiosqlite:///:memory:"
    )
    async with engine.connect() as conn:
        await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.execute(text("PRAGMA journal_mode=MEMORY;"))

    return engine

@pytest.fixture()
def provider(engine: AsyncEngine) -> SQLAlchemyProvider:
    return SQLAlchemyProvider(engine)

@pytest.fixture()
def container(provider: SQLAlchemyProvider) -> Container:
    container: Container = make_container(provider)
    return container

@pytest.fixture()
def repo(container: Container) -> RepositorySQLA:
    with container() as request_container:
        repo: Repository = request_container.get(Repository)
        assert isinstance(repo, RepositorySQLA)
    return repo

@pytest.fixture(autouse=True)
async def setup_db(engine: AsyncEngine, repo: RepositorySQLA):
    await repo.init_db(engine)
