from dishka import Provider, Scope, provide

from server.utils.config import (
    AppConfig,
    MinimapKeyPointConfig,
    NeuralNetworkConfig,
    ServerSettings,
    VideoPreprocessingConfig,
)


class ConfigProvider(Provider):
    """
    Предоставляет доступ к конфигурации сервера с помощью инжекции зависимостей.
    """

    def __init__(self, app_config: AppConfig):
        super().__init__()
        self.app_config: AppConfig = app_config

    @provide(scope=Scope.REQUEST)
    def get_app_config(self) -> AppConfig:
        return self.app_config

    @provide(scope=Scope.REQUEST)
    def get_minimap_config(self) -> MinimapKeyPointConfig:
        return self.app_config.minimap_config

    @provide(scope=Scope.REQUEST)
    def get_nn_config(self) -> NeuralNetworkConfig:
        return self.app_config.nn_config

    @provide(scope=Scope.REQUEST)
    def get_server_settings(self) -> ServerSettings:
        return self.app_config.server_settings

    @provide(scope=Scope.REQUEST)
    def get_video_processing_config(self) -> VideoPreprocessingConfig:
        return self.app_config.video_processing
