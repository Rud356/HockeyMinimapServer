from typing import Protocol, runtime_checkable

from server.data_storage.protocols.dataset_repo import DatasetRepo
from server.data_storage.protocols.frames_repo import FramesRepo
from server.data_storage.protocols.map_data_repo import MapDataRepo
from server.data_storage.protocols.player_data_repo import PlayerDataRepo
from server.data_storage.protocols.transaction_manager import TransactionManager
from server.data_storage.protocols.user_repo import UserRepo
from server.data_storage.protocols.video_repo import VideoRepo


@runtime_checkable
class Repository(Protocol):
    transaction: TransactionManager

    @property
    def player_data_repo(self) -> PlayerDataRepo:
        ...

    @property
    def dataset_repo(self) -> DatasetRepo:
        ...

    @property
    def frames_repo(self) -> FramesRepo:
        ...

    @property
    def user_repo(self) -> UserRepo:
        ...

    @property
    def video_repo(self) -> VideoRepo:
        ...

    @property
    def map_data_repo(self) -> MapDataRepo:
        ...
