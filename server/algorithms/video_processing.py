from pathlib import Path
from typing import Any, Optional

import cv2
import ffmpeg

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

    def get_sample_from_video(self, file: Path, *, frame_timestamp: Optional[float] = None, frame_index: Optional[int] = None):
        video_info = self.probe_video(file)

        if frame_timestamp is not None and frame_index is not None:
            raise ValueError("Must only specify either frame timestamp or frame index")

        try:
            cap = cv2.VideoCapture(str(file.resolve()))
            if cap.isOpened():
                if frame_index is not None:
                    assert isinstance(frame_index, int), \
                        f"Invalid type of frame_index parameter (must be int, got {type(frame_index)})"

                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

                if frame_timestamp is not None:
                    assert isinstance(frame_timestamp, float), \
                        f"Invalid type of frame_index parameter (must be int, got {type(frame_timestamp)})"

                    cap.set(cv2.CAP_PROP_POS_MSEC, frame_timestamp)

                ret, frame = cap.read()

                if ret:
                    return frame

                else:
                    raise InvalidFileFormat("Unexpected file format or file not readable by cv2")

        except Exception as e:
            pass

    @staticmethod
    def probe_video(file: Path) -> dict[str, Any]:
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
