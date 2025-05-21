import asyncio
import time
from asyncio import Lock, sleep

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, NoReturn


class FileLock:
    """
    Блокирует доступ к конкретному файлу в рамках всего приложения.
    """

    def __init__(self, cleanup_time: float = 120):
        self.modification_lock = Lock()
        self.locks: dict[str | Path, tuple[Lock, float]] = {}
        self.cleanup_time: float = cleanup_time

    @asynccontextmanager
    async def lock_file(self, path: Path | str, timeout: float | None = None) -> AsyncGenerator[None, None]:
        """
        Блокирует параллельный доступ к файлу.

        :param path: Путь до файла.
        :param timeout: Время ожидания взятия блокировки ресурса.
        :return: Контекстный менеджер блокировки.
        :raise TimeoutError: Получено исключение по времени.
        """
        current_lock: Lock | None
        current_lock, _ = self.locks.get(path, (None, None))
        async with self.modification_lock:
            if current_lock is None:
                current_lock = Lock()

            self.locks[path] = current_lock, time.time()

        try:
            async with asyncio.timeout(timeout):
                await current_lock.acquire()
            yield

        finally:
            if current_lock.locked():
                current_lock.release()

    async def run_cleanup_loop(self) -> NoReturn:
        """
        Запускает сервис отчистки блокировок доступа к файлам.

        :return: Ничего.
        """
        while True:
            await sleep(self.cleanup_time)
            await self.search_and_destroy_unused_locks()

    async def search_and_destroy_unused_locks(self) -> None:
        """
        Ищет все редко запрашиваемые и давно не использованные блокировки доступа.

        :return: Ничего.
        """
        checked_at = time.time()

        async with self.modification_lock:
            for path, (lock, time_accessed) in self.locks.items():
                if lock.locked():
                    self.locks[path] = lock, checked_at

                elif round(checked_at - time_accessed) >= self.cleanup_time and not lock.locked():
                    # Cleanup
                    del self.locks[path]
