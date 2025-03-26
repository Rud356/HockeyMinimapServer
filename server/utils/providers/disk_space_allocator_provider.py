from dishka import Provider, Scope, provide

from server.algorithms.disk_space_allocator import DiskSpaceAllocator


class DiskSpaceAllocatorProvider(Provider):
    """
    Предоставляет доступ к разделяемому ресурсу дискового пространства.
    """
    def __init__(self, disk_space_allocator: DiskSpaceAllocator):
        super().__init__()
        self.disk_space_allocator = disk_space_allocator

    @provide(scope=Scope.REQUEST)
    def disk_allocator(self) -> DiskSpaceAllocator:
        return self.disk_space_allocator
