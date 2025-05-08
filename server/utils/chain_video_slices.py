from typing import AsyncGenerator, Sequence

import cv2

from .async_video_reader import async_video_reader
from server.algorithms.data_types import CV_Image


async def chain_video_slices(
    video_reader: cv2.VideoCapture, slice_ranges: Sequence[tuple[int, int]]
) -> AsyncGenerator[tuple[int, CV_Image], None]:
    """
    Получает отдельные кадры в переданных промежутках кадров.

    :param video_reader: Объект чтения кадров.
    :param slice_ranges: Промежутки с какого кадра по какой кадр вычитывать кадры.
    :return: Генератор считанных кадров, содержащий номер кадра и сам кадр.
    """
    # validate ranges
    for start_frame, end_frame in slice_ranges:
        if start_frame > end_frame:
            raise ValueError(f"{end_frame=} must be greater or equal to {start_frame=}")

        if start_frame < 0:
            raise ValueError(f"{start_frame=} must be greater or equal to 0")

        if end_frame < 0:
            raise ValueError(f"{end_frame=} must be greater or equal to 0")

        video_reader.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        current_frame_num: int = start_frame
        video_generator: AsyncGenerator[CV_Image, None] = async_video_reader(video_reader)

        async for frame in video_generator:
            yield current_frame_num, frame
            current_frame_num += 1

            if current_frame_num >= end_frame:
                break
