import asyncio
from asyncio import Queue
from concurrent.futures import Executor
from concurrent.futures.thread import ThreadPoolExecutor
from typing import AsyncGenerator, Optional

import cv2
import numpy

from server.algorithms.enums import Team
from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.data_storage.dto import PointDTO
from server.data_storage.dto.player_data_dto import PlayerDataDTO


class MapVideoRendererService:
    """
    Отображает игроков на поле на основе данных и выводит видео.
    """

    def __init__(
        self,
        renderer_pool_executor: Executor,
        video_writer: cv2.VideoWriter,
        frame_buffer_limit: int = 10,
        point_size: int = 25,
        home_color: tuple[int, int, int] = (135, 206, 235),
        away_color: tuple[int, int, int] = (250, 224, 51),
        referee_color: tuple[int, int, int] = (128, 77, 65)
    ):
        assert frame_buffer_limit >= 1, "Must always have frame buffer limit set to 1 or more as integer"
        self.video_writer: cv2.VideoWriter = video_writer
        self.renderer_pool_executor: Executor = renderer_pool_executor
        self.draw_queue: Queue[numpy.ndarray | None] = Queue(frame_buffer_limit)
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

        with self.renderer_pool_executor as write_executor:
            while (frame := await self.draw_queue.get()) is not None:
                await loop.run_in_executor(write_executor, self.video_writer.write, frame)

        self.video_writer.release()

    async def data_renderer(self, map_frame: numpy.ndarray) -> AsyncGenerator[int, list[PlayerDataDTO] | None]:
        """
        Рисует кадры мини-карты.

        :param map_frame: Исходное изображение мини-карты.
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

            map_copy = map_frame.copy()
            updated_frame = await self.draw_frame_data(map_copy, fetched_frame_data)
            await self.draw_queue.put(updated_frame)

            counter += 1

    async def draw_frame_data(self, map_data: numpy.ndarray, players_data: list[PlayerDataDTO]) -> numpy.ndarray:
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
        map_frame: numpy.ndarray,
        tracking_id: int,
        map_point_position: PointDTO,
        class_id: PlayerClasses,
        team_id: Optional[Team] = None,
        player_name: Optional[str] = None
    ) -> numpy.ndarray:
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

        match class_id:
            case PlayerClasses.Referee:
                map_frame = cv2.circle(map_frame, point_position, self.point_size, self.referee_color, thickness=-1)
                map_frame = cv2.circle(
                    map_frame, point_position, self.point_size, (16, 16, 16), thickness=2, lineType=cv2.LINE_AA
                )
                map_frame = self.draw_text(map_frame, point_position, "R")

            case PlayerClasses.Player:
                if team_id == Team.Home:
                    map_frame = cv2.circle(map_frame, point_position, self.point_size, self.home_color, thickness=-1)

                elif team_id == Team.Away:
                    map_frame = cv2.circle(map_frame, point_position, self.point_size, self.away_color, thickness=-1)

                else:
                    # Grey for unknown team
                    map_frame = cv2.circle(map_frame, point_position, self.point_size, (127, 127, 127), thickness=-1)

                # draw text with player name or id
                map_frame = cv2.circle(
                    map_frame, point_position, self.point_size,
                    (16, 16, 16), thickness=2, lineType=cv2.LINE_AA
                )

                if player_name:
                    map_frame = self.draw_text(map_frame, point_position, str(player_name))

                else:
                    map_frame = self.draw_text(map_frame, point_position, str(tracking_id))

            case PlayerClasses.Goalie:
                if team_id == Team.Home:
                    map_frame = cv2.circle(map_frame, point_position, self.point_size, self.home_color, thickness=-1)

                elif team_id == Team.Away:
                    map_frame = cv2.circle(map_frame, point_position, self.point_size, self.away_color, thickness=-1)

                else:
                    # Grey for unknown team
                    map_frame = cv2.circle(
                        map_frame, point_position, self.point_size, (127, 127, 127), thickness=-1
                    )

                # draw text with G for goalie
                map_frame = cv2.circle(
                    map_frame, point_position, self.point_size, (16, 16, 16), thickness=2, lineType=cv2.LINE_AA
                )
                map_frame = self.draw_text(map_frame, point_position, "G")

        return map_frame

    def draw_text(self, image: numpy.ndarray, center: tuple[int, int], text: str) -> numpy.ndarray:
        """
        Рисует текст на игроке.

        :param image: Изображение, на котором рисуется.
        :param center: Центр текста.
        :param text: Текст для рисования.
        :return: Обновленное изображение.
        """
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1
        font_thickness = 2
        (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, font_thickness)
        text_x = center[0] - text_width // 2
        text_y = center[1] + self.point_size // 2

        return cv2.putText(
            image,
            text,
            (text_x, text_y),
            font,
            font_scale,
            (200, 200, 200),
            font_thickness,
            lineType=cv2.LINE_AA
        )
