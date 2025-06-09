import asyncio
import sys
import tomllib
from argparse import Namespace

from dishka import make_async_container
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from server.data_storage.sql_implementation.sqla_provider import SQLAlchemyProvider
from server.minimap_server import MinimapServer
from server.utils.config import AppConfig

args: Namespace = MinimapServer.parse_launch_arguments()

with open(args.config_path, mode="rb") as f:
    config_data = AppConfig(**tomllib.load(f))

config_data.local_mode = args.local_mode or config_data.local_mode
server = MinimapServer(config_data)

if args.drop_db and args.init_db:
    tmp_engine: AsyncEngine = create_async_engine(config_data.db_connection_string)
    tmp_sqla_provider: SQLAlchemyProvider = SQLAlchemyProvider(tmp_engine)
    asyncio.run(server.drop_db(tmp_engine, make_async_container(tmp_sqla_provider)))
    asyncio.run(server.init_db(tmp_engine, make_async_container(tmp_sqla_provider)))
    sys.exit(0)

elif args.drop_db:
    tmp_engine = create_async_engine(config_data.db_connection_string)
    tmp_sqla_provider = SQLAlchemyProvider(tmp_engine)
    asyncio.run(server.drop_db(tmp_engine, make_async_container(tmp_sqla_provider)))
    sys.exit(0)

elif args.init_db:
    tmp_engine = create_async_engine(config_data.db_connection_string)
    tmp_sqla_provider = SQLAlchemyProvider(tmp_engine)
    asyncio.run(server.init_db(tmp_engine, make_async_container(tmp_sqla_provider)))
    sys.exit(0)

app = server.app
server.finish_setup()

def run_server() -> None:
    server.start()
