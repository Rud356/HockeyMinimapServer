from pathlib import Path

from sqlalchemy import Select, func

from server.algorithms.video_processing import VideoPreprocessingConfig, VideoProcessing
from server.data_storage.exceptions import DataIntegrityError
from server.data_storage.sql_implementation.tables import Frame
from .fixtures import *

test_video_directory: Path = Path(__file__).parent.parent.parent / "static" / "videos"
test_video_path: Path = test_video_directory / "converted_demo.mp4"


@pytest.fixture()
def processing_config() -> VideoPreprocessingConfig:
    return VideoPreprocessingConfig(video_width=1280, video_height=720, crf=30)


@pytest.fixture()
def video_processing_obj(processing_config: VideoPreprocessingConfig) -> VideoProcessing:
    return VideoProcessing(processing_config)

@pytest.fixture()
def video_probe_data(video_processing_obj) -> dict[str, str]:
    return video_processing_obj.probe_video(test_video_path)


@pytest.fixture()
def video_fps(video_processing_obj, video_probe_data) -> float:
    return video_processing_obj.get_fps_from_probe(video_probe_data)


@pytest.fixture()
def video_frames_count(video_processing_obj, video_probe_data) -> int:
    return video_processing_obj.get_frames_count_from_probe(video_probe_data)


async def test_creating_video_frames(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    async with repo.transaction as tr:
        frames_inserted = await tr.session.scalar(
            Select(func.count("*")).where(Frame.video_id == video.video_id)
        )

    assert frames_inserted == video_frames_count


async def test_creating_frames_without_video(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    with pytest.raises(DataIntegrityError):
        async with repo.transaction as tr:
            await repo.frames_repo.create_frames(1, video_frames_count)


async def test_creating_invalid_frames_count(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    with pytest.raises(ValueError):
        async with repo.transaction as tr:
            await repo.frames_repo.create_frames(1, -1)

    with pytest.raises(ValueError):
        async with repo.transaction as tr:
            await repo.frames_repo.create_frames(1, 500_001)


async def test_creating_duplicate_frames(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)

    with pytest.raises(DataIntegrityError):
        async with repo.transaction as tr:
            await repo.frames_repo.create_frames(1, video_frames_count)
