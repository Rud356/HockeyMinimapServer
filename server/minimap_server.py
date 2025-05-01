import argparse
import asyncio
import tempfile
import time
import typing
from argparse import Namespace
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

import uvicorn
from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import (
    DishkaRoute,
    FastapiProvider,
    setup_dishka,
)
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from starlette.middleware.base import BaseHTTPMiddleware

from server.algorithms.disk_space_allocator import DiskSpaceAllocator
from server.algorithms.video_processing import VideoProcessing
from server.controllers.services.user_authorization_service import UserAuthorizationService
from server.controllers.user_authentication import UserAuthenticationEndpoint
from server.controllers.users_managment import UserManagementEndpoint
from server.controllers.video_endpoints import VideoUploadEndpoint
from server.data_storage.sql_implementation.repository_sqla import RepositorySQLA
from server.data_storage.sql_implementation.sqla_provider import SQLAlchemyProvider
from server.utils.config import AppConfig
from server.utils.providers import (
    ConfigProvider,
    DiskSpaceAllocatorProvider,
    ExecutorsProvider,
    RenderServiceLimitsProvider,
    UserAuthorizationProvider,
)


class MinimapServer:
    app: FastAPI

    def __init__(self, config: AppConfig, **fastapi_app_config) -> None:
        self.app = FastAPI(
            lifespan=self.lifespan,
            host=config.server_settings.host,
            port=config.server_settings.port,
            **fastapi_app_config
        )
        self.config: AppConfig = config
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )

        # Initialize middlewares
        if config.enable_gzip_compression:
            self.app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)

        self.app.add_middleware(BaseHTTPMiddleware, dispatch=self.add_process_time_header)
        self.router: APIRouter = APIRouter(route_class=DishkaRoute)
        self.reload_dirs: list[str] = [str(config.static_path.resolve())]

        # Initialize engine and provider
        engine: AsyncEngine = create_async_engine(config.db_connection_string)
        sqla_provider = SQLAlchemyProvider(engine)

        # Init if database is in memory automatically
        if "sqlite+aiosqlite:///:memory:" in config.db_connection_string:
            self.init_db(engine, sqla_provider)

        temp_dir = Path(tempfile.gettempdir())
        temp_disk_allocator: DiskSpaceAllocator = DiskSpaceAllocator(temp_dir)
        static_path_disk_allocator: DiskSpaceAllocator

        # Check if folders are on same disk to know if it needs to be single or two different disk
        # space allocators
        if temp_dir.stat().st_dev != config.static_path.stat().st_dev:
             static_path_disk_allocator = DiskSpaceAllocator(config.static_path)
        else:
            static_path_disk_allocator = temp_disk_allocator

        # Initialize container for providers
        container: AsyncContainer = make_async_container(
            DiskSpaceAllocatorProvider(
                temp_disk_allocator,
                static_path_disk_allocator
            ),
            ConfigProvider(config),
            FastapiProvider(),
            sqla_provider,
            UserAuthorizationProvider(),
            RenderServiceLimitsProvider(
                config.minimap_rendering_workers,
                config.minimap_frame_buffer
            ),
            ExecutorsProvider(
                config.video_processing_workers,
                config.players_data_extraction_workers
            )
        )

        setup_dishka(container=container, app=self.app)

        # Setup routes
        api = APIRouter(prefix="/api", route_class=DishkaRoute)
        VideoUploadEndpoint(api, VideoProcessing(config.video_processing))
        UserManagementEndpoint(api)
        UserAuthenticationEndpoint(api)

        self.app.mount("/static", StaticFiles(directory=config.static_path), name="static")
        self.register_routes(api)

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
        response: Response = await call_next(request)
        process_time = time.perf_counter() - start_time
        response.headers["Server-Timing"] = f"app;dur={round(process_time * 1000, 4)}"
        return response

    @staticmethod
    def parse_launch_arguments() -> Namespace:
        """
        Получает параметры запуска при инициализации приложения.

        :return: Пространство имен с полученными переменными.
        """
        parser: argparse.ArgumentParser = argparse.ArgumentParser(
            prog="server",
            add_help=False,
            description="Сервер разметки видео для поиска позиций игроков на видеозаписях хоккейных игр"
        )
        parser.add_argument(
            '-h', '--help', action='help', default=argparse.SUPPRESS,
            help='Показывает сообщение с помощью и закрывает программу'
        )
        parser.add_argument(
            "--init-db", action="store_true", default=False,
            dest="init_db",
            help="Инициализирует базу данных при запуске, не запуская сервер"
        )
        parser.add_argument(
            "--drop-db", action="store_true", default=False,
            dest="drop_db",
            help="Удаляет базу данных при запуске, не запуская сервер"
        )
        parser.add_argument(
            "--config", "-c", default=Path("./config.toml"), type=Path,
            dest="config_path",
            help="Устанавливает путь до файла конфигурации приложения"
        )
        parser.add_argument(
            "--local-mode", action="store_true", default=None,
            dest="local_mode",
            help="Запускает сервер в локальном режиме работы с пользователем по умолчанию под логином Admin"
        )

        return parser.parse_args()

    @asynccontextmanager
    async def lifespan(self, app: FastAPI) -> AsyncGenerator[None, Any]:
        yield
        await app.state.dishka_container.close()

    @staticmethod
    def init_db(engine: AsyncEngine, sqla_provider: SQLAlchemyProvider) -> None:
        """
        Инициализирует базу данных.

        :param engine: Подключение к базе данных.
        :param sqla_provider: Объект получения других объектов взаимодействия с БД.
        :return: Ничего.
        """
        tmp_repo: RepositorySQLA = typing.cast(RepositorySQLA, sqla_provider.get_repository())
        asyncio.run(tmp_repo.init_db(engine))

    @staticmethod
    def drop_db(engine: AsyncEngine, sqla_provider: SQLAlchemyProvider) -> None:
        """
        Удаляет базу данных.

        :param engine: Подключение к базе данных.
        :param sqla_provider: Объект получения других объектов взаимодействия с БД.
        :return: Ничего.
        """
        tmp_repo: RepositorySQLA = typing.cast(RepositorySQLA, sqla_provider.get_repository())
        asyncio.run(tmp_repo.drop_db(engine))

    def start(self) -> None:
        uvicorn.run(
            self.app,
            host=self.config.server_settings.host,
            port=self.config.server_settings.port,
            reload_dirs=self.reload_dirs
        )

