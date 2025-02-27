from pathlib import Path
from typing import Any, Optional

import cv2
import ffmpeg
import numpy
from numpy import ndarray

from server.algorithms.exceptions.invalid_file_format import InvalidFileFormat
from server.utils.config import VideoPreprocessingConfig


class VideoProcessing:
    """
    Отвечает за обработку видео и получение информации о видеофайле.

    :param processing_config: Объект конфигурации обработки.
    """
    processing_config: VideoPreprocessingConfig


    def __init__(self, video_processing_config: VideoPreprocessingConfig):
        self.processing_config = video_processing_config

    def get_sample_from_video(
        self, file: Path, *, frame_timestamp: Optional[float] = None, frame_index: Optional[int] = None
    ) -> tuple[ndarray, dict[str, Any]]:
        """
        Получает один кадр из видео.

        :param file: Путь до файла.
        :param frame_timestamp: Временная метка, с которой получаем кадр.
        :param frame_index: Номер кадра, с которого получаем кадр.
        :return: Кадр и метаинформация о видеофайле.
        """
        video_info = self.probe_video(file)
        frame: Optional[numpy.ndarray] = None

        if frame_timestamp is not None and frame_index is not None:
            raise ValueError("Must only specify either frame timestamp or frame index")

        try:
            cap = cv2.VideoCapture(str(file.resolve()))
            if cap.isOpened():
                # Set timestamp
                if frame_index is not None:
                    self.set_capture_frame_index(cap, frame_index)
                if frame_timestamp is not None:
                    self.set_capture_timestamp(cap, frame_timestamp)

                # Set output frame
                ret, frame_data = cap.read()
                if ret:
                    frame = frame_data
                else:
                    raise InvalidFileFormat("Unexpected file format or file not readable by cv2")

        except Exception as e:
            raise InvalidFileFormat("Error decoding video") from e

        return frame, video_info

    # TODO: Add method for picking correction using lenscorrect and for converting video

    @staticmethod
    def probe_video(file: Path) -> dict[str, Any]:
        """
        Получает информацию о формате файлов и проверяет, является ли файл видео файлом.

        :param file: Путь до файла.
        :return: Информация о файле.
        """
        if not file.is_file():
            raise FileNotFoundError("Video file to get sample from not found on disk")

        IMAGE_FORMATS = {
            'png', 'jpeg', 'mjpeg', 'bmp', 'gif'
        }
        try:
            data: list[dict[str, Any]]  = ffmpeg.probe(str(file))["streams"]
            video_streams: list[dict[str, Any]] = [stream for stream in data if stream['codec_type'] == "video"]
            if len(video_streams) != 1:
                raise InvalidFileFormat("Video expected to have only one video stream")

            return video_streams[0]

        except ffmpeg.Error:
            raise InvalidFileFormat("File is not supported by ffmpeg")

    @staticmethod
    def set_capture_timestamp(cap: cv2.VideoCapture, timestamp: float) -> None:
        """
        Устанавливает позицию захвата видео на кадр по временной метке.

        :param cap: Источник захвата.
        :param timestamp: Временная метка.
        :return: Нет возврата.
        """
        assert isinstance(timestamp, float), \
            f"Invalid type of frame_index parameter (must be int, got {type(timestamp)})"

        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp)

    @staticmethod
    def set_capture_frame_index(cap: cv2.VideoCapture, frame_index: int) -> None:
        """
        Устанавливает позицию захвата видео на кадр по номеру кадра.

        :param cap: Источник захвата.
        :param frame_index: Номер кадра.
        :return: Нет возврата.
        """
        assert isinstance(frame_index, int), \
            f"Invalid type of frame_index parameter (must be int, got {type(frame_index)})"

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
