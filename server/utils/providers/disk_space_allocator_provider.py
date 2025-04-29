from typing import NewType

from dishka import Provider, Scope, provide

from server.algorithms.disk_space_allocator import DiskSpaceAllocator

StaticDirSpaceAllocator = NewType("StaticDirSpaceAllocator", DiskSpaceAllocator)
TmpDirSpaceAllocator = NewType("TmpDirSpaceAllocator", DiskSpaceAllocator)


class DiskSpaceAllocatorProvider(Provider):
    """
    Предоставляет доступ к разделяемому ресурсу дискового пространства.
    """
    def __init__(
        self,
        tmp_disk_space_allocator: DiskSpaceAllocator,
        static_dir_disk_space_allocator: DiskSpaceAllocator
    ):
        super().__init__()
        self.tmp_disk_space_allocator: TmpDirSpaceAllocator = TmpDirSpaceAllocator(tmp_disk_space_allocator)
        self.static_dir_space_allocator: StaticDirSpaceAllocator = StaticDirSpaceAllocator(static_dir_disk_space_allocator)

    @provide(scope=Scope.REQUEST)
    def tmp_disk_allocator(self) -> TmpDirSpaceAllocator:
        return self.tmp_disk_space_allocator

    @provide(scope=Scope.REQUEST)
    def static_dir_disk_allocator(self) -> StaticDirSpaceAllocator:
        return self.static_dir_space_allocator
