from pathlib import Path
from typing import AsyncGenerator, Protocol, runtime_checkable

from server.algorithms.data_types.frame_data import FrameData
# TODO: Implement rendering minimap based on provided data


@runtime_checkable
class MinimapRendererService(Protocol):
    """
    Описывает протокол для сервиса отрисовки мини-карты.
    """
    async def render_minimap(
        self,
        fps: float,
        player_frame_data: AsyncGenerator[FrameData, None],
        dest_file: Path,
        ignore_exists: bool
    ) -> Path:
        """
        Генерирует мини-карту

        :param fps: Количество кадров в секунду.
        :param player_frame_data: Итератор с информацией об игроках на протяжении всего файла.
        :param dest_file: Путь до конечного файла мини-карты.
        :param ignore_exists: Нужно ли игнорировать существование выведенной мини-карты.
        :return: Путь до выведенной мини-карты.
        """
        pass
