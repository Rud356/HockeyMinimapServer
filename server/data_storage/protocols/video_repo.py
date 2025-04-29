from pathlib import Path
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

    async def create_new_video(
        self,
        fps: float,
        source_video_path: str
    ) -> VideoDTO:
        """
        Создает новое видео в базе данных.

        :param fps: FPS видео.
        :param source_video_path: Относительный путь до файла от корня хранилища видео.
        :return: Информация о созданном объекте видео.
        """

    async def list_all_uploaded_videos_names(self, from_directory: Path) -> list[Path]:
        """
        Выводит список видео файлов из папки для их хранения в относительных путях.

        :param from_directory: Из какой директории вывести список файлов.
        :return: Список названий видео файлов.
        """

    async def get_videos(self, limit: int = 100, offset: int = 0) -> list[VideoDTO]:
        """
        Выводит список информации о видео в системе.

        :param limit: Количество записей.
        :param offset: Отступ от первой записи.
        :return: Список информации о видео.
        """

    async def get_video(self, video_id: int) -> Optional[VideoDTO]:
        """
        Получает информацию о конкретном видео.

        :param video_id: Идентификатор видео.
        :return: Информация о видео.
        :raises ValueError: Если данные на вход или выход невозможно привести к нужным типам.
        """

    async def set_flag_video_is_converted(
        self, video_id: int, flag_value: bool, from_directory: Path, converted_video_path: Path
    ) -> bool:
        """
        Устанавливает пометку завершения конвертации форматов видео.

        :param video_id: Идентификатор видео.
        :param flag_value: В какое значение установить флаг.
        :param from_directory: Путь до корневой директории с видео.
        :param converted_video_path: Путь, по которому доступно видео.
        :return: Новое значение флага.
        :raise ValueError: Если видео не существует по указанному пути или не найдено видео в БД.
        """

    async def set_flag_video_is_processed(self, video_id: int, flag_value: bool) -> bool:
        """
        Устанавливает пометку завершения обработки видео.

        :param video_id: Идентификатор видео.
        :param flag_value: В какое значение установить флаг.
        :return: Новое значение флага.
        :raise ValueError: Если видео не существует по указанному пути или не найдено видео в БД.
        """

    async def adjust_corrective_coefficients(self, video_id: int, k1: float, k2: float) -> None:
        """
        Изменяет коэффициенты коррекции видео.

        :param video_id: Идентификатор видео.
        :param k1: Первичный коэффициент коррекции.
        :param k2: Вторичный коэффициент коррекции.
        :raise NotFoundError: Если видео не найдено в БД.
        :raise DataIntegrityError: Если коэффициенты были неверно заданы.
        :return: Ничего.
        """

    async def set_camera_position(self, video_id: int, camera_position: CameraPosition) -> bool:
        """
        Изменяет положение камеры.

        :param video_id: Идентификатор видео.
        :param camera_position: Позиция камеры в пространстве.
        :return: Внесены ли изменения.
        :raises NotFoundError: Если не найдено видео в бд.
        :raises ValueError: Если переданная позиция камеры не является валидной.
        """
