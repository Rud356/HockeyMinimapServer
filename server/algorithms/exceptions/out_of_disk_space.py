from pathlib import Path


class OutOfDiskSpace(MemoryError):
    """
    Представляет ошибку при нехватке места на диске для сохранения ресурса.
    """
    def __init__(self, path: Path, required_space: int, free_real_disk_space: int, free_runtime_disk_space: int):
        self.path = path
        self.required_space = required_space
        self.free_real_disk_space: int = free_real_disk_space
        self.free_runtime_disk_space: int = free_runtime_disk_space

    def __repr__(self) -> str:
        """
        Представляет читаемый текст ошибки.

        :return: Сообщение ошибки.
        """
        return (
            f"Not enough disk space to allocate: tried to allocate"
            f" {round(self.required_space / (1024 ** 3), 2)}GiB"
            f" but got only {round(self.free_runtime_disk_space / (1024 ** 3), 2)}GiB of runtime space"
            f" (real free disk space is {round(self.free_real_disk_space / (1024 ** 3), 2)})"
        )
