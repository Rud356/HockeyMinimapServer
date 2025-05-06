import tomllib
from argparse import Namespace

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from server.minimap_server import AppConfig, MinimapServer
from server.data_storage.sql_implementation.sqla_provider import SQLAlchemyProvider

args: Namespace = MinimapServer.parse_launch_arguments()

with open(args.config_path, mode="rb") as f:
    config_data = AppConfig(**tomllib.load(f))

config_data.local_mode = args.local_mode or config_data.local_mode
server = MinimapServer(config_data)

if args.drop_db and args.init_db:
    tmp_engine: AsyncEngine = create_async_engine(config_data.db_connection_string)
    tmp_sqla_provider: SQLAlchemyProvider = SQLAlchemyProvider(tmp_engine)
    server.drop_db(tmp_engine, tmp_sqla_provider)
    server.init_db(tmp_engine, tmp_sqla_provider)
    exit(0)

elif args.drop_db:
    tmp_engine = create_async_engine(config_data.db_connection_string)
    tmp_sqla_provider = SQLAlchemyProvider(tmp_engine)
    server.drop_db(tmp_engine, tmp_sqla_provider)
    exit(0)

elif args.init_db:
    tmp_engine = create_async_engine(config_data.db_connection_string)
    tmp_sqla_provider = SQLAlchemyProvider(tmp_engine)
    server.init_db(tmp_engine, tmp_sqla_provider)
    exit(0)

app = server.app
server.finish_setup()

def run_server():
    server.start()
