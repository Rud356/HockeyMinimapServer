from collections.abc import Mapping
from pathlib import Path

MINIMAP_PATH: Path = Path("./resources/minimap.svg")


class MiniMap:
    key_points: Mapping[int, tuple[int, int]]
    minimap_path: Path

    def __init__(self):
        self.key_points = {}
        self.minimap_path = MINIMAP_PATH
