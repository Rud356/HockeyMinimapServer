from typing import Optional, Protocol, runtime_checkable

from server.algorithms.enums.camera_position import CameraPosition
from server.data_storage.dto.video_dto import VideoDTO
from server.data_storage.protocols.transaction_manager import TransactionManager


@runtime_checkable
class VideoRepo(Protocol):
    """
    Управляет данными о видео.
    """
    transaction: TransactionManager

    async def list_all_uploaded_videos_names(self) -> list[str]:
        """
        Выводит список видео файлов из папки для их хранения.

        :return: Список названий видео файлов.
        """
        ...

    async def get_videos(self, limit: int = 100, offset: int = 0) -> list[VideoDTO]:
        """
        Выводит список информации о видео в системе.

        :param limit: Количество записей.
        :param offset: Отступ от первой записи.
        :return: Список информации о видео.
        """
        ...

    async def get_video(self, video_id: int) -> Optional[VideoDTO]:
        """
        Получает информацию о конкретном видео.

        :param video_id: Идентификатор видео.
        :return: Информация о видео.
        """
        ...

    async def set_flag_video_is_converted(self) -> bool:
        """
        Устанавливает пометку завершения конвертации форматов видео.

        :return: Успешно занесены данные.
        """
        ...

    async def set_flag_video_is_processed(self) -> bool:
        """
        Устанавливает пометку завершения обработки видео.

        :return: Успешно занесены данные.
        """
        ...

    async def adjust_corrective_coefficients(self, k1: float, k2: float) -> None:
        """
        Изменяет коэффициенты коррекции видео.

        :param k1: Первичный коэффициент коррекции.
        :param k2: Вторичный коэффициент коррекции.
        :return: Ничего.
        """
        ...

    async def set_camera_position(self, video_id: int, camera_position: CameraPosition) -> bool:
        """
        Изменяет положение камеры.

        :param video_id: Идентификатор видео.
        :param camera_position: Позиция камеры в пространстве.
        :return: Внесены ли изменения.
        """
