import tomllib
from pathlib import Path

from server.minimap_server import MinimapServer, AppConfig

__version__ = "0.0.2"
DEFAULT_CONFIG_PATH: Path = Path("./config.toml")

with open(DEFAULT_CONFIG_PATH, mode="rb") as f:
    config_data = AppConfig(**tomllib.load(f))

server = MinimapServer(config_data)
server.finish_setup()
app = server.app
