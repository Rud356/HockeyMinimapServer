import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator, cast

import cv2

from server.algorithms.data_types import CV_Image


async def async_video_reader(video_reader: cv2.VideoCapture) -> AsyncGenerator[CV_Image, None]:
    """
    Создает асинхронный генератор, получающий кадры из видео.

    :param video_reader: Объект для чтения видео.
    :return: Генератор чтения кадров.
    """
    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

    with ThreadPoolExecutor(max_workers=1) as thread:
        while video_reader.isOpened():
            ret, frame = await loop.run_in_executor(thread, video_reader.read, None)
            if not ret:
                break

            yield cast(CV_Image, frame)
