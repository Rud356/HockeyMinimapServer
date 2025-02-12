import asyncio
from contextlib import asynccontextmanager

import uvicorn
from dishka.integrations.fastapi import (
    DishkaRoute,
    FromDishka,
    FastapiProvider,
    inject,
    setup_dishka,
)
from dishka import AsyncContainer, make_async_container, Provider, provide, Scope
from fastapi import FastAPI, APIRouter

from server.utils.config import AppConfig, ServerConfig, VideoPreprocessingConfig
from server.utils.config.neural_netwroks_config import NeuralNetworkConfig


class BackgroundService:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def __call__(self, *args, **kwargs):
        while True:
            print(await self.queue.get())


class TestProvider(Provider):
    def __init__(self, service):
        super().__init__()
        self.service = service

    @provide(scope=Scope.REQUEST)
    def provide_service(self) -> BackgroundService:
        return self.service


class MinimapServer:
    app: FastAPI

    def __init__(self, config: AppConfig, **fastapi_app_config):
        self.app = FastAPI(
            lifespan=self.lifespan,
            host=config.server_settings.host,
            port=config.server_settings.port,
            **fastapi_app_config
        )
        self.router: APIRouter = APIRouter(route_class=DishkaRoute)

        self.service = BackgroundService()
        container: AsyncContainer = make_async_container(
            # YourProvider(),
            TestProvider(self.service),
            FastapiProvider()
        )

        setup_dishka(container=container, app=self.app)

    def register_routes(self, new_router: APIRouter, prefix: str = ""):
        self.router.include_router(new_router, prefix=prefix)

    def finish_setup(self):
        self.app.include_router(self.router)

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        asyncio.create_task(self.service())
        yield
        await self.app.state.dishka_container.close()

    def start(self):
        uvicorn.run(self.app)

class Route:
    router: APIRouter

    def __init__(self, id=123):
        self.id_ = id
        self.router = APIRouter(route_class=DishkaRoute)
        self.router.get("/get")(self.get)

    async def get(self) -> str:
        return "123" + str(self.id_)

server = MinimapServer(
    AppConfig(debug_visualization=True, db_connection_string="",
        nn_config=NeuralNetworkConfig(field_detection_model_path="", player_detection_model_path="", max_batch_size=5),
        server_settings=ServerConfig(host="localhost", port=1080, is_local_instance=True),
        video_processing=VideoPreprocessingConfig(fps=30, video_width=1280, video_height=720, crf=30))
)
router = Route().router


@server.router.get(
    "/put"
)
async def example(serv: FromDishka[BackgroundService]) -> str:
    await serv.queue.put("Example text")
    print("Added to queue")
    return "Hello world! 234"


server.register_routes(router, "/api")

server.register_routes(Route(88005553535).router, "/api/test")

server.finish_setup()
server.register_routes(router, "/api")
server.start()
