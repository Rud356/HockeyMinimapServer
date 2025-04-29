from concurrent.futures import Executor
from concurrent.futures.thread import ThreadPoolExecutor
from typing import NewType

from dishka import Provider, Scope, provide

VideoProcessingWorker = NewType("VideoProcessingWorker", Executor)
PlayersDataExtractionWorker = NewType("PlayersDataExtractionWorker", Executor)


class ExecutorsProvider(Provider):
    """
    Предоставляет доступ к исполнителям синхронных задач с ограничением количества рабочих потоков.
    """
    def __init__(
        self,
        video_processing_workers: int,
        players_data_extraction_workers: int
    ):
        super().__init__()
        self.video_processing_workers: VideoProcessingWorker = VideoProcessingWorker(
            ThreadPoolExecutor(video_processing_workers)
        )
        self.player_data_extraction_workers: PlayersDataExtractionWorker = PlayersDataExtractionWorker(
            ThreadPoolExecutor(players_data_extraction_workers)
        )

    @provide(scope=Scope.REQUEST)
    def get_video_processing_worker(self) -> VideoProcessingWorker:
        return self.video_processing_workers

    @provide(scope=Scope.REQUEST)
    def get_players_data_extraction_workers(self) -> PlayersDataExtractionWorker:
        return self.player_data_extraction_workers
