import asyncio
import contextlib
import pathlib
import shutil
import tempfile
import uuid
from typing import Any, AsyncGenerator

from server.algorithms.data_types.disk_usage import DiskUsage


class InvalidAllocationSize(ValueError):
    """
    Вызывается когда выделяемый объем меньше 1 байта.
    """
    
    
class InvalidAllocationOverPropositionFactor(ValueError):
    """
    Вызывается когда фактор умножения не является допустимым (допустимые значения от 1 до 1000).
    """


class DiskSpaceAllocator:
    """
    Вспомогательный класс для выделения места на диске и управления местом для хранения данных.
    """

    def __init__(self, directory: pathlib.Path = pathlib.Path(tempfile.gettempdir())):
        self.directory: pathlib.Path = directory
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
        Возвращает соотношение общего объема диска к

        :return:
        """
        return self.total_free_space / self.current_disk_usage.total

    def get_disk_usage(self) -> DiskUsage:
        return DiskUsage(*shutil.disk_usage(self.directory))

    @contextlib.asynccontextmanager
    async def preallocate_disk_space(
        self, preallocate_space: int, over_proposition_factor: float = 1.3
    ) -> AsyncGenerator[int, Any]:
        """
        Предварительно выделяет место на диске для использования, и по закрытию контекстного менеджера
            актуализирует реально доступный объем.

        :param preallocate_space: Количество предварительно выделенного места для проекта.
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
                raise MemoryError(
                    f"Not enough memory to store project: tried to allocate"
                    f" {round(preallocate_space / (1024**3), 2)}GiB"
                    f" but got only {round(self.total_free_space / (1024**3), 2)}GiB"
                )

        yield preallocate_space

        async with self.disk_allocation_lock:
            del self.active_space_reservations_bins[bin_id]
            self.current_disk_usage = self.get_disk_usage()


if __name__ == "__main__":
    async def demo_alloc(alloc, size):
        async with alloc.preallocate_disk_space(size*(1024**3)) as data:
            await asyncio.sleep(2)


    async def main():
        alloc = DiskSpaceAllocator()
        asyncio.create_task(demo_alloc(alloc, 10))
        asyncio.create_task(demo_alloc(alloc, 12))
        await asyncio.sleep(1)
        asyncio.create_task(demo_alloc(alloc, 50))
        asyncio.create_task(demo_alloc(alloc, 60))
        print(DiskUsage(alloc.current_disk_usage.total, alloc.total_reserved_space, alloc.total_free_space))
        await demo_alloc(alloc, 10)
        print(DiskUsage(alloc.current_disk_usage.total, alloc.total_reserved_space, alloc.total_free_space))


    asyncio.run(main())
