from typing import Protocol, runtime_checkable

from server.data_storage.protocols.transaction_manager import TransactionManager


@runtime_checkable
class FramesRepo(Protocol):
    """
    Управляет информацией о кадрах.
    """

    transaction: TransactionManager

    async def create_frames(self, video_id: int, frames_count: int) -> int:
        """
        Создает множество кадров для конкретного видео.

        :param video_id: Идентификатор видео.
        :param frames_count: Количество кадров для создания.
        :return: Количество созданных кадров.
        :raise ValueError: Если количество кадров меньше 1 или больше 500 тысяч.
        :raise DataIntegrityError: Если нарушено ограничение по существованию видео.
        """
        ...
