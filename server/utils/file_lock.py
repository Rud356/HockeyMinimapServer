import time
from asyncio import Lock, sleep

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, NoReturn


class FileLock:
    def __init__(self, cleanup_time: float = 120):
        self.modification_lock = Lock()
        self.locks: dict[str | Path, tuple[Lock, float]] = {}
        self.cleanup_time: float = cleanup_time

    @asynccontextmanager
    async def lock_file(self, path: Path | str) -> AsyncGenerator[None, None]:
        """
        Блокирует параллельный доступ к файлу.

        :param path: Путь до файла.
        :return: Контекстный менеджер блокировки.
        """
        current_lock, created_at = self.locks.get(path, (None, None))

        if current_lock is None:
            current_lock = Lock()

        async with self.modification_lock:
            self.locks[path] = current_lock, time.time()

        async with current_lock:
            yield None

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
