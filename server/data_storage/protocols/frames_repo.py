from typing import Protocol, runtime_checkable

from server.data_storage.dto.frame_data_dto import FrameDataDTO
from server.data_storage.protocols.transaction_manager import TransactionManager


@runtime_checkable
class FramesRepo(Protocol):
    transaction: TransactionManager

    async def create_frames(self, video_id: int, frames_count: int) -> int:
        ...

    async def get_frames_data(self, limit: int = 120, offset: int = 0) -> list[FrameDataDTO]:
        ...
