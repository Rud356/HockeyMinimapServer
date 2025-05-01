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
