import time
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import (
    DishkaRoute,
    FastapiProvider,
    setup_dishka,
)
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from server.algorithms.disk_space_allocator import DiskSpaceAllocator
from server.controllers.video_upload import VideoUploadEndpoint
from server.utils.config import (
    AppConfig,
    MinimapKeyPointConfig,
    NeuralNetworkConfig,
    ServerSettings,
    VideoPreprocessingConfig,
)
from server.utils.providers import ConfigProvider
from server.utils.providers.disk_space_allocator_provider import DiskSpaceAllocatorProvider


class MinimapServer:
    app: FastAPI

    def __init__(self, config: AppConfig, **fastapi_app_config):
        self.app = FastAPI(
            lifespan=self.lifespan,
            host=config.server_settings.host,
            port=config.server_settings.port,
            **fastapi_app_config
        )
        # Initialize middlewares
        if config.enable_gzip_compression:
            self.app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)

        self.app.add_middleware(BaseHTTPMiddleware, dispatch=self.add_process_time_header)
        self.router: APIRouter = APIRouter(route_class=DishkaRoute)

        container: AsyncContainer = make_async_container(
            DiskSpaceAllocatorProvider(DiskSpaceAllocator()),
            ConfigProvider(config),
            FastapiProvider()
        )

        setup_dishka(container=container, app=self.app)

    def register_routes(self, new_router: APIRouter, prefix: str = "") -> None:
        """
        Добавляет новые эндпоинты к основному роутеру.

        :param new_router: Новый роутер для включения.
        :param prefix: Префикс для добавления роута.
        :return: Ничего.
        """
        self.router.include_router(new_router, prefix=prefix)

    def finish_setup(self) -> None:
        """
        Завершает подготовку FastAPI сервера для работы.

        :return: Ничего.
        """
        self.app.include_router(self.router)

    @staticmethod
    async def add_process_time_header(request: Request, call_next) -> Response:
        """
        Дает дополнительную информацию о времени обработки запроса на сервере для отладки.

        :param request: Запрос для обработки.
        :param call_next: Следующий вызов.
        :return: Ответ на запрос.
        """
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["X-Process-Time"] = str(round(process_time, 4))
        return response

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        yield
        await app.state.dishka_container.close()

    def start(self):
        uvicorn.run(self.app)


MINIMAP_KEY_POINTS = MinimapKeyPointConfig(**
    {
        "top_left_field_point": {"x": 16, "y": 88},
        "bottom_right_field_point": {"x": 1247, "y": 704},

        "left_goal_zone": {"x": 116, "y": 396},
        "right_goal_zone": {"x": 1144, "y": 396},

        "center_line_top": {"x": 630, "y": 92},
        "center_line_bottom": {"x": 630, "y": 700},

        "left_blue_line_top": {"x": 423, "y": 92},
        "left_blue_line_bottom": {"x": 423, "y": 700},

        "right_blue_line_top": {"x": 838, "y": 92},
        "right_blue_line_bottom": {"x": 838, "y": 700},

        "left_goal_line_top": {"x": 99, "y": 105},
        "left_goal_line_bottom": {"x": 99, "y": 360},

        "left_goal_line_after_zone_top": {"x": 99, "y": 433},
        "left_goal_line_after_zone_bottom": {"x": 99, "y": 688},

        "right_goal_line_top": {"x": 1162, "y": 105},
        "right_goal_line_bottom": {"x": 1162, "y": 360},

        "right_goal_line_after_zone_top": {"x": 1162, "y": 433},
        "right_goal_line_after_zone_bottom": {"x": 1162, "y": 688},

        "center_circle": {"x": 630, "y": 396},
        "red_circle_top_left": {"x": 241, "y": 243},
        "red_circle_top_right": {"x": 1020, "y": 243},
        "red_circle_bottom_left": {"x": 241, "y": 550},
        "red_circle_bottom_right": {"x": 1020, "y": 550}
    }
)

server = MinimapServer(
    AppConfig(
        enable_gzip_compression=False,
        players_data_extraction_workers=4,
        minimap_rendering_workers=4,
        debug_visualization=True,
        db_connection_string="Helloworld",
        nn_config=NeuralNetworkConfig(
            field_detection_model_path=Path(""), player_detection_model_path=Path(""), max_batch_size=5
        ),
        minimap_config=MINIMAP_KEY_POINTS,
        server_settings=ServerSettings(host="localhost", port=1080, is_local_instance=True),
        video_processing=VideoPreprocessingConfig(video_width=1280, video_height=720, crf=30)
    )
)

api = APIRouter(prefix="/api", route_class=DishkaRoute)
VideoUploadEndpoint(api)

server.register_routes(api)
server.finish_setup()

if __name__ == "__main__":
    server.start()
