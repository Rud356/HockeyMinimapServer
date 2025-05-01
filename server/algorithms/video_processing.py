import shutil
import tempfile
import typing
from functools import reduce
from pathlib import Path
from typing import Any, Optional

import cv2
import ffmpeg

from server.algorithms.data_types import CV_Image
from server.algorithms.exceptions.invalid_file_format import InvalidFileFormat
from server.utils.config import VideoPreprocessingConfig


class VideoProcessing:
    """
    Отвечает за обработку видео и получение информации о видеофайле.
    """
    processing_config: VideoPreprocessingConfig

    def __init__(self, video_processing_config: VideoPreprocessingConfig):
        self.processing_config = video_processing_config

    def get_sample_from_video(
        self, file: Path, *, frame_timestamp: Optional[float] = None, frame_index: Optional[int] = None
    ) -> tuple[CV_Image | None, dict[str, Any]]:
        """
        Получает один кадр из видео.

        :param file: Путь до файла.
        :param frame_timestamp: Временная метка в секундах, с которой получаем кадр.
        :param frame_index: Номер кадра, с которого получаем кадр.
        :return: Кадр и метаинформация о видеофайле.
        :raise FileNotFound: Файл не найден на диске.
        :raise ValueError: Использовано два варианта временных меток одновременно,
            или временная метка вне длительности видео.
        :raise KeyError: Временная метка конца не найдена в метаданных.
        :raise InvalidFileFormat: Неподдерживаемый формат файла предоставлен в качестве файла.
        """
        video_info = self.probe_video(file)
        frame: Optional[CV_Image] = None

        if frame_timestamp is not None and frame_index is not None:
            raise ValueError("Must only specify either frame timestamp or frame index")

        try:
            cap = cv2.VideoCapture(str(file.resolve()))
            if cap.isOpened():
                # Set timestamp
                if frame_index is not None:
                    self.set_capture_frame_index(cap, frame_index)

                if frame_timestamp is not None:
                    end_timestamp: float = self.convert_ffmpeg_timestamp_to_seconds(video_info["tags"]["DURATION"])
                    if not self.is_valid_timestamp(frame_timestamp, end_timestamp):
                        raise ValueError("Invalid timestamp provided")

                    self.set_capture_timestamp(cap, frame_timestamp)

                # Set output frame
                ret, frame_data = cap.read()
                if ret:
                    frame = typing.cast(CV_Image, frame_data)
                else:
                    raise InvalidFileFormat("Unexpected file format or file not readable by cv2")

        except KeyError as e:
            raise KeyError("Duration information from metadata not found") from e

        except ValueError:
            raise

        except Exception as e:
            raise InvalidFileFormat("Error decoding video") from e

        return frame, video_info

    def render_correction_sample(
        self,
        source_file: Path,
        k1: float = 0.0,
        k2: float = 0.0,
        frame_timestamp: Optional[float] = None
    ) -> tuple[CV_Image, dict[str, Any]]:
        """
        Применяет фильтр коррекции искажений к видео и выводи один кадр из видео.

        :param source_file: Исходное видео без коррекции.
        :param k1: Коэффициент коррекции видео 1.
        :param k2: Коэффициент коррекции видео 2.
        :param frame_timestamp: Временная метка для перехода к получению кадра в секундах.
        :return: Кадр и техническая информация об исходном видео.
        :raise FileNotFound: Файл не найден на диске.
        :raise ValueError: Временная метка вне длительности видео.
        :raise KeyError: Временная метка конца не найдена в метаданных.
        :raise InvalidFileFormat: Неподдерживаемый формат файла предоставлен в качестве файла.
        """
        if frame_timestamp is None:
            frame_timestamp = 0.0

        video_info = self.probe_video(source_file)
        frame: Optional[CV_Image] = None

        try:
            end_timestamp: float = self.convert_ffmpeg_timestamp_to_seconds(video_info["duration"])
            if not self.is_valid_timestamp(frame_timestamp, end_timestamp):
                raise ValueError("Invalid timestamp provided")

        except KeyError as e:
            raise KeyError("Duration information from metadata not found") from e

        with tempfile.TemporaryDirectory(prefix="hmms_") as temp_dir:
            temp_dir_path: Path = Path(temp_dir)
            temp_frame: Path = temp_dir_path / "frame.png"
            # Execute convertion and correction
            (
                ffmpeg.input(
                    str(source_file),
                    hwaccel=self.processing_config.hwaccel,
                    ss=f"{frame_timestamp:.3f}"
                )
                .output(
                    str(temp_frame),
                    vf=f"lenscorrection=k1={k1}:k2={k2}",
                    frames="1",
                    preset=f"{self.processing_config.preset}",
                    crf=f"{self.processing_config.crf}",
                    loglevel="quiet",
                    movflags='faststart'
                )
                .global_args("-y")
                .run()
            )

            sample_frame: CV_Image = typing.cast(CV_Image, cv2.imread(str(temp_frame)))
            if sample_frame is None:
                raise InvalidFileFormat(
                    "Can't read the file, expected to have output from ffmpeg, but none received")

            frame = sample_frame

        return frame, video_info

    def render_corrected_video(
        self,
        source_file: Path,
        dest_file: Path,
        k1: float = 0.0,
        k2: float = 0.0
    ) -> dict[str, Any]:
        """
        Применяет фильтр коррекции искажений к видео и выводит его в новую папку.

        :param dest_file: Путь для переноса конечного файла после обработки.
        :param source_file: Исходное видео без коррекции.
        :param k1: Коэффициент коррекции видео 1.
        :param k2: Коэффициент коррекции видео 2.
        :return: техническая информация о видео.
        :raise FileNotFound: Файл не найден на диске.
        :raise InvalidFileFormat: Неподдерживаемый формат файла предоставлен в качестве файла.
        """
        # Checking video does exist and has correct file format that can be processed
        self.probe_video(source_file)

        with tempfile.TemporaryDirectory(prefix="hmms_") as temp_dir:
            temp_dir_path: Path = Path(temp_dir)
            temp_video: Path = temp_dir_path / "video.mp4"
            # Execute convertion and correction
            # Scale down without upscale and preserve aspect ratio
            scale_filter = (
                f"scale='min({self.processing_config.video_width},iw)':'min({self.processing_config.video_height},ih)'"
                ":force_original_aspect_ratio=decrease"
            )
            (
                ffmpeg.input(
                    str(source_file),
                    hwaccel=self.processing_config.hwaccel
                )
                .output(
                    str(temp_video),
                    vf=f"{scale_filter},lenscorrection=k1={k1}:k2={k2}",
                    preset=f"{self.processing_config.preset}",
                    crf=f"{self.processing_config.crf}",
                    loglevel="quiet",
                    movflags='faststart'
                )
                .global_args("-y")
                .run()
            )

            video_info = self.probe_video(temp_video)
            shutil.move(temp_video, dest_file)

        return video_info

    def compress_video(self, source_file: Path, dest_file: Path) -> dict[str, Any]:
        """
        Сжимает видео в размере для оптимизации передачи по сети.

        :param source_file: Исходный файл.
        :param dest_file: Целевой файл.
        :return: Информация о выведенном видео.
        :raise FileNotFound: Файл не найден на диске.
        :raise InvalidFileFormat: Неподдерживаемый формат файла предоставлен в качестве файла.
        """
        # Checking video does exist and has correct file format that can be processed
        self.probe_video(source_file)

        with tempfile.TemporaryDirectory(prefix="hmms_") as temp_dir:
            temp_dir_path: Path = Path(temp_dir)
            temp_video: Path = temp_dir_path / "video.mp4"
            # Execute convertion and correction
            # Scale down without upscale and preserve aspect ratio
            (
                ffmpeg.input(
                    str(source_file),
                    hwaccel=self.processing_config.hwaccel
                )
                .output(
                    str(temp_video),
                    preset=f"{self.processing_config.preset}",
                    crf=f"{self.processing_config.crf}",
                    loglevel="quiet",
                    movflags='faststart'
                )
                .global_args("-y")
                .run()
            )

            video_info = self.probe_video(temp_video)
            shutil.move(temp_video, dest_file)

        return video_info

    @staticmethod
    def probe_video(file: Path) -> dict[str, Any]:
        """
        Получает информацию о формате файлов и проверяет, является ли файл видео файлом.

        :param file: Путь до файла.
        :return: Информация о файле
        :raise FileNotFound: Файл не найден на диске.
        :raise InvalidFileFormat: Неподдерживаемый формат видео.
        """
        if not file.is_file():
            raise FileNotFoundError("Video file to get sample from not found on disk")

        IMAGE_FORMATS: frozenset[str] = frozenset(
            {'png', 'jpeg', 'mjpeg', 'bmp', 'gif'}
        )
        try:
            data: list[dict[str, Any]]  = ffmpeg.probe(str(file))["streams"]
            video_streams: list[dict[str, Any]] = [
                stream for stream in data
                    if stream['codec_type'] == "video" and stream["codec_name"] not in IMAGE_FORMATS
            ]
            if len(video_streams) != 1:
                raise InvalidFileFormat("Video expected to have only one video stream")

            return video_streams[0]

        except ffmpeg.Error as err:
            raise InvalidFileFormat("File is not supported by ffmpeg") from err

    @staticmethod
    def set_capture_timestamp(cap: cv2.VideoCapture, timestamp: float) -> None:
        """
        Устанавливает позицию захвата видео на кадр по временной метке.

        :param cap: Источник захвата.
        :param timestamp: Временная метка в секундах.
        :return: Нет возврата.
        """
        assert isinstance(timestamp, float), \
            f"Invalid type of frame_index parameter (must be int, got {type(timestamp)})"

        # Converted to ms
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp*1000)

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

    @staticmethod
    def convert_ffmpeg_timestamp_to_seconds(timestamp: str) -> float:
        """
        Получает из строки длительности от ffmpeg время в секундах.

        :param timestamp: Строка временной метки в формате hh:mm:ss.mm.
        :return: Временная метка в секундах.
        :raise ValueError: Не верный формат временной метки.
        """
        try:
            timestamp_value: float = float(timestamp)

        except ValueError:
            pass

        else:
            return timestamp_value

        parts = timestamp.split(":")

        if len(parts) != 3:
            raise ValueError("Unexpected timestamp format, must have 3 parts of hours, minutes and seconds")

        converted_parts: float = reduce(
            lambda previous, mul_part: previous + (mul_part[0] * mul_part[1]),
            zip([60*60, 60, 1], [float(part) for part in parts]),
            0.0
        )
        return converted_parts

    @staticmethod
    def is_valid_timestamp(timestamp: float, end_timestamp: float) -> bool:
        """
        Проверка нахождения временной метки в промежутке значений длительности видео.

        :param timestamp: Временная метка для проверки в секундах.
        :param end_timestamp: Временная метка конца видео.
        :return: Является ли верной временной меткой.
        """
        return 0.0 <= timestamp <= end_timestamp

    @staticmethod
    def get_fps_from_probe(data: dict[str, str]) -> float:
        """
        Получает фреймрейт видео.

        :param data: Данные из ffmpeg о видео.
        :return: Количество кадров в секунду.
        """
        r_frame_rate = data['r_frame_rate']
        num, denominator = map(int, r_frame_rate.split('/'))
        return num / denominator

    @staticmethod
    def get_frames_count_from_probe(data: dict[str, str]) -> int:
        """
        Получает количество кадров в видео.

        :param data: Данные из ffmpeg о видео.
        :return: Количество кадров.
        """
        return int(data['nb_frames'])
