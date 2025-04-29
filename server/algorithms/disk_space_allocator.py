import asyncio
import contextlib
import pathlib
import shutil
import tempfile
import uuid
from typing import Any, AsyncGenerator

from server.algorithms.data_types.disk_usage import DiskUsage
from server.algorithms.exceptions import InvalidAllocationOverPropositionFactor
from server.algorithms.exceptions import InvalidAllocationSize
from server.algorithms.exceptions import OutOfDiskSpace


class DiskSpaceAllocator:
    """
    Вспомогательный класс для выделения места на диске и управления местом для хранения данных.
    """

    def __init__(
        self, directory: pathlib.Path = pathlib.Path(tempfile.gettempdir())
    ):
        self._directory: pathlib.Path = directory
        self.current_disk_usage: DiskUsage = self.get_disk_usage()
        self.disk_allocation_lock: asyncio.Lock = asyncio.Lock()
        self.active_space_reservations_bins: dict[uuid.UUID, int] = {}

    @property
    def total_reserved_space(self) -> int:
        """
        Получает зарезервированное место на диске.

        :return: Сумма зарезервированного места под проекты на диске.
        """
        return sum(self.active_space_reservations_bins.values())

    @property
    def total_free_space(self) -> int:
        """
        Объем свободного места на диске за вычетом зарезервированного места.

        :return: Объем свободного и незарезервированного места проектами.
        """
        return self.current_disk_usage.free - self.total_reserved_space

    @property
    def free_disk_space_ratio(self) -> float:
        """
        Возвращает соотношение общего объема диска к занятому и предварительно выделенному месту.

        :return: Соотношение.
        """
        return self.total_free_space / self.current_disk_usage.total

    def get_disk_usage(self) -> DiskUsage:
        """
        Получает информацию о свободном дисковом пространстве.

        :return: Информация о свободном пространстве на физическом накопителе.
        """
        return DiskUsage(*shutil.disk_usage(self._directory))

    @contextlib.asynccontextmanager
    async def preallocate_disk_space(
        self, preallocate_space: int, over_proposition_factor: float = 1.1
    ) -> AsyncGenerator[int, Any]:
        """
        Предварительно выделяет место на диске для использования, и по закрытию контекстного менеджера
            актуализирует реально доступный объем.

        :param preallocate_space: Количество предварительно выделенного места для проекта в байтах.
        :param over_proposition_factor: Коэффициент прозапаса места для работы с проектом.
        :return: Генератор выделенного объема на диске.
        :raise InvalidAllocationSize: Когда объем выделяемого места меньше 1 байта или не является целым числом.
        :raise InvalidAllocationOverPropositionFactor: Когда коэффициент прозапаса места меньше 1 или больше 1000.
        :raise MemoryError: Когда недостаточно места для сохранения данных на диск.
        """
        if not isinstance(preallocate_space, int) or preallocate_space < 1:
            raise InvalidAllocationSize(
                f"Too small allocation size: got {preallocate_space}b pre-allocation"
            )

        if not (1 <= over_proposition_factor <= 1000):
            raise InvalidAllocationOverPropositionFactor(
                f"Invalid over proposition scaling: got {over_proposition_factor}"
            )
        
        bin_id = uuid.uuid1()
        async with self.disk_allocation_lock:
            preallocate_space = round(preallocate_space * over_proposition_factor)

            if self.total_free_space > preallocate_space:
                self.active_space_reservations_bins[bin_id] = preallocate_space

            else:
                raise OutOfDiskSpace(
                    self._directory,
                    preallocate_space,
                    self.current_disk_usage.free,
                    self.total_free_space
                )
        yield preallocate_space

        async with self.disk_allocation_lock:
            del self.active_space_reservations_bins[bin_id]
            self.current_disk_usage = self.get_disk_usage()
