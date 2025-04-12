from concurrent.futures import Executor
from concurrent.futures.thread import ThreadPoolExecutor
from typing import NewType

from dishka import Provider, Scope, provide

RenderWorker = NewType("RenderWorker", Executor)
RenderBuffer = NewType("RenderBuffer", int)


class RenderServiceLimitsProvider(Provider):
    """
    Предоставляет доступ к сервису отрисовки видео.
    """
    def __init__(self, minimap_rendering_workers: int, buffer_size: int):
        super().__init__()
        self.render_threadpool: Executor = ThreadPoolExecutor(minimap_rendering_workers)
        self.buffer_size: int = buffer_size

    @provide(scope=Scope.REQUEST)
    def get_minimap_renderer_worker(self) -> RenderWorker:
        return RenderWorker(self.render_threadpool)

    @provide(scope=Scope.REQUEST)
    def get_minimap_renderer_buffer_size(self) -> RenderBuffer:
        return RenderBuffer(self.buffer_size)
