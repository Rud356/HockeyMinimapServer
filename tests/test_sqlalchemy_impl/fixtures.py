import pytest
import pytest_asyncio  # noqa: used as plugin
from dishka import Container, make_container
from sqlalchemy.ext.asyncio import create_async_engine

from server.data_storage.sql_implementation.repository_sqla import RepositorySQLA, Repository
from server.data_storage.sql_implementation.sqla_provider import SQLAlchemyProvider


@pytest.fixture()
def engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:")

@pytest.fixture()
def provider(engine) -> SQLAlchemyProvider:
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
async def setup_db(engine, repo: RepositorySQLA):
    print("DB Initialized")
    await repo.init_db(engine)
