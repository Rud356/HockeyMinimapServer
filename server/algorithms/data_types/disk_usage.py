from typing import NamedTuple


class DiskUsage(NamedTuple):
    total: int
    used: int
    free: int

    def to_gigabytes_representation(self, scale_size: int = 1024) -> tuple[str, str, str]:
        """
        Переводит размер места из байтов в гигабайты.

        :param scale_size: Размерность приставок (для кило-, мега- и т.д.) на каждый шаг.
        :return: Строка с отформатированными размерами.
        """
        giga_scale: int = scale_size ** 3

        return (
            str(round(self.total / giga_scale, 2)),
            str(round(self.used / giga_scale, 2)),
            str(round(self.free / giga_scale, 2))
        )

    def __str__(self) -> str:
        total, used, free = self.to_gigabytes_representation()
        return f"Disk space: (total = {total}GB, used = {used}GB, free = {free}GB)"

    def __repr__(self) -> str:
        return str(self)
