import asyncio
import shutil
import tempfile
import typing
from asyncio import Queue
from concurrent.futures import Executor
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from typing import AsyncGenerator, Optional

import cv2
import ffmpeg

from server.algorithms.data_types import CV_Image
from server.algorithms.enums import Team
from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.data_storage.dto import PointDTO
from server.data_storage.dto.player_data_dto import PlayerDataDTO
from server.utils.config import VideoPreprocessingConfig

FILL_CIRCLE_THICKNESS: int = -1


class MapVideoRendererService:
    """
    Отображает игроков на поле на основе данных и выводит видео.
    """

    def __init__(
        self,
        renderer_pool_executor: Executor,
        fps: int | float,
        output_dest: Path,
        map_frame: CV_Image,
        video_processing_config: VideoPreprocessingConfig,
        frame_buffer_limit: int = 10,
        point_size: int = 25,
        home_color: tuple[int, int, int] = (0, 157, 255),
        away_color: tuple[int, int, int] = (255, 138, 0),
        referee_color: tuple[int, int, int] = (156, 156, 156)
    ):
        assert frame_buffer_limit >= 1, "Must always have frame buffer limit set to 1 or more as integer"
        assert fps > 5, "Must specify fps at least"
        self.fps: float = fps
        self.output_dest: Path = output_dest.resolve()
        self.map_frame: CV_Image = map_frame
        self.video_processing_config: VideoPreprocessingConfig = video_processing_config
        self.renderer_pool_executor: Executor = renderer_pool_executor
        self.draw_queue: Queue[CV_Image | None] = Queue(frame_buffer_limit)
        self.point_size = point_size
        self.home_color: tuple[int, int, int] = home_color
        self.away_color: tuple[int, int, int] = away_color
        self.referee_color: tuple[int, int, int] = referee_color

    async def run(self) -> None:
        """
        Запускает асинхронный сервис записи видео с мини-картой.

        :return: Ничего не возвращает, останавливается передачей None в очередь на вывод.
        """
        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        height, width, *_ = self.map_frame.shape
        additional_options = {}
        additional_input_options = {}
        if len(self.video_processing_config.preset):
            additional_options["preset"] = self.video_processing_config.preset

        if len(self.video_processing_config.hwaccel_output_format):
            additional_input_options["hwaccel_output_format"] = self.video_processing_config.hwaccel_output_format

        with tempfile.TemporaryDirectory(prefix="hmms_map_render_") as temp_dir:
            temp_video_path: Path = Path(temp_dir) / self.output_dest.name
            process = (
                ffmpeg.input("pipe:", format="rawvideo", pix_fmt="bgr24",
                    s='{}x{}'.format(width, height),
                    hwaccel=self.video_processing_config.hwaccel,
                    loglevel="quiet",
                    **additional_input_options
                )
                .filter('pad', width='ceil(iw/2)*2', height='ceil(ih/2)*2')
                .output(
                    str(temp_video_path.resolve()),
                    pix_fmt='yuv420p',
                    vcodec=f"{self.video_processing_config.codec}",
                    crf=f"{self.video_processing_config.crf}",
                    movflags='faststart',
                    **additional_options
                )
                .global_args("-y")
                .run_async(pipe_stdin=True)
            )

            with self.renderer_pool_executor as write_executor:
                while (frame := await self.draw_queue.get()) is not None:
                    await loop.run_in_executor(write_executor, process.stdin.write, frame.tobytes())

                process.stdin.close()
                await loop.run_in_executor(
                    write_executor,
                    process.wait
                )
                await loop.run_in_executor(
                    write_executor,
                    partial(
                        shutil.move,
                        temp_video_path.resolve(), self.output_dest.resolve()
                    )
                )

    async def data_renderer(self) -> AsyncGenerator[int, list[PlayerDataDTO] | None]:
        """
        Рисует кадры мини-карты.

        :return: Асинхронный генератор, выдающий номер обработанного кадра (начиная с 0), и
            принимающий список информации об игроках в кадре, останавливаемый передачей значения None.
        """
        counter: int = 0

        while True:
            fetched_frame_data: list[PlayerDataDTO] | None = yield counter

            if fetched_frame_data is None:
                # Stop execution and cleanup rendering
                await self.draw_queue.put(None)
                return

            map_copy = self.map_frame.copy()
            updated_frame = await self.draw_frame_data(map_copy, fetched_frame_data)
            await self.draw_queue.put(updated_frame)

            counter += 1

    async def draw_frame_data(self, map_data: CV_Image, players_data: list[PlayerDataDTO]) -> CV_Image:
        """
        Асинхронно рисует информацию на кадре.
        :param map_data: Изображение мини-карты.
        :param players_data: Список информации об игроках.
        :return: Обновленное изображение.
        """
        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

        with ThreadPoolExecutor(1) as threadpool:
            for player_data in players_data:
                map_data = await loop.run_in_executor(
                    threadpool,
                    self.draw_player_point,
                    map_data,
                    # Parameters from player block
                    player_data.tracking_id,
                    player_data.player_on_minimap,
                    player_data.class_id,
                    player_data.team_id,
                    player_data.player_name
                )

        return map_data

    def draw_player_point(
        self,
        map_frame: CV_Image,
        tracking_id: int,
        map_point_position: PointDTO,
        class_id: PlayerClasses,
        team_id: Optional[Team] = None,
        player_name: Optional[str] = None
    ) -> CV_Image:
        """
        Рисует точку игрока на поле.

        :param map_frame: Кадр мини-карты.
        :param tracking_id: Номер отслеживания.
        :param map_point_position: Положение отслеживания.
        :param class_id: Класс игрока (рефери, вратарь, игрок).
        :param team_id: Идентификатор команды.
        :param player_name: Пользовательское название игрока.
        :return: Нарисованный кадр.
        """
        point_position: tuple[int, int] = int(map_point_position.x), int(map_point_position.y)

        # Unknown player team color and text color
        team_color: tuple[int, int, int] = (232, 232, 232)
        team_text_color: tuple[int, int, int] = (0, 0, 0)

        match class_id:
            case PlayerClasses.Referee:
                map_frame = self.draw_point(
                    map_frame,
                    "R",
                    self.referee_color,
                    (255, 255, 255),
                    point_position
                )

            case PlayerClasses.Player:
                # Overriding default unknown team color
                if team_id == Team.Home:
                    team_color = self.home_color

                elif team_id == Team.Away:
                    team_color = self.away_color

                # Choosing what to render as player name
                if player_name:
                    map_frame = self.draw_point(
                        map_frame,
                        str(player_name),
                        team_color,
                        team_text_color,
                        point_position
                    )

                else:
                    map_frame = self.draw_point(
                        map_frame,
                        str(tracking_id),
                        team_color,
                        team_text_color,
                        point_position
                    )

            case PlayerClasses.Goalie:
                # Overriding default unknown team color
                if team_id == Team.Home:
                    team_color = self.home_color

                elif team_id == Team.Away:
                    team_color = self.away_color

                # Choosing what to render as player name
                if player_name:
                    map_frame = self.draw_point(
                        map_frame,
                        str(player_name),
                        team_color,
                        team_text_color,
                        point_position
                    )

                else:
                    map_frame = self.draw_point(
                        map_frame,
                        "G",
                        team_color,
                        team_text_color,
                        point_position
                    )

        return map_frame

    def draw_point(
        self,
        map_frame: CV_Image,
        text: str,
        color: tuple[int, int, int],
        text_color: tuple[int, int, int],
        position: tuple[int, int],
        outline_thickness: int = 1
    ) -> CV_Image:
        """
        Рисует точку игрока на мини-карте.

        :param map_frame: Кадр карты.
        :param text: Текст отрисованной точки.
        :param color: Цвет точки.
        :param text_color: Цвет текста.
        :param position: Положение точки.
        :param outline_thickness: Ширина обводки.
        :return: Обновленный кадр мини-карты с новой точкой.
        """

        # Main circle
        map_frame = typing.cast(
            CV_Image,
            cv2.circle(
                map_frame,
                position,
                self.point_size,
                color,
                thickness=FILL_CIRCLE_THICKNESS
            )
        )

        # Outline circle
        map_frame = typing.cast(
            CV_Image,
            cv2.circle(
                map_frame,
                position,
                self.point_size,
                (16, 16, 16),
                thickness=outline_thickness,
                lineType=cv2.LINE_AA
            )
        )

        # Text
        map_frame = self.draw_text(map_frame, position, text, text_color)

        return map_frame


    def draw_text(
        self,
        image: CV_Image,
        center: tuple[int, int],
        text: str,
        color: tuple[int, int, int] = (0, 0, 0)
    ) -> CV_Image:
        """
        Рисует текст на игроке.

        :param image: Изображение, на котором рисуется.
        :param center: Центр текста.
        :param text: Текст для рисования.
        :param color: Цвет текста.
        :return: Обновленное изображение.
        """
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        font_thickness = 2
        (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, font_thickness)
        text_x = center[0] - text_width // 2
        text_y = center[1] + self.point_size // 2

        return typing.cast(CV_Image,
            cv2.putText(
                image,
                text,
                (text_x, text_y),
                font,
                font_scale,
                color,
                font_thickness,
                lineType=cv2.LINE_AA
            )
        )
