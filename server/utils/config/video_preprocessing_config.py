from pydantic import BaseModel


class VideoPreprocessingConfig(BaseModel):
    """
    Конфигурация параметров для конвертации видео с помощью FFmpeg.
    """
    fps: int
    video_width: int
    video_height: int
    crf: int
