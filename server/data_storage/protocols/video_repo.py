from typing import Protocol, runtime_checkable

from server.data_storage.dto.video_dto import VideoDTO
from server.data_storage.protocols.transaction_manager import TransactionManager


@runtime_checkable
class VideoRepo(Protocol):
    transaction: TransactionManager

    async def list_all_uploaded_videos_names(self) -> list[str]:
        ...

    async def get_videos(self, limit: int = 100, offset: int = 0) -> list[VideoDTO]:
        ...

    async def get_video(self, video_id: int) -> VideoDTO:
        ...

    async def set_flag_video_is_converted(self) -> bool:
        ...

    async def set_flag_video_is_processed(self) -> bool:
        ...

    async def adjust_corrective_coefficients(self, k1: float, k2: float) -> None:
        ...
