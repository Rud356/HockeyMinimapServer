from pydantic import BaseModel, Field


class VideoPreprocessingConfig(BaseModel):
    """
    Конфигурация параметров для конвертации видео с помощью FFmpeg.
    """
    hwaccel: str = Field(default="auto")
    hwaccel_output_format: str = Field(default="")
    codec: str = Field(default="h264")
    video_width: int = Field(default=1280)
    video_height: int = Field(default=720)
    preset: str = Field(default="fast")
    crf: int = Field(default=27)
    target_bitare: str = Field(default="2.5M")
    maxrate: str = Field(default="5M")
    bufsize: str = Field("10M")
    loglevel: str = Field(default="quiet")
