from pathlib import Path

from server.algorithms.enums import CameraPosition
from server.algorithms.video_processing import VideoPreprocessingConfig, VideoProcessing
from server.data_storage.exceptions import DataIntegrityError, NotFoundError
from .fixtures import *

test_video_directory: Path = Path(__file__).parent.parent.parent / "tests" / "videos"
test_video_path: Path = test_video_directory / "converted_demo.mp4"


@pytest.fixture()
def processing_config() -> VideoPreprocessingConfig:
    return VideoPreprocessingConfig(video_width=1280, video_height=720, crf=30)


@pytest.fixture()
def video_processing_obj(processing_config: VideoPreprocessingConfig) -> VideoProcessing:
    return VideoProcessing(processing_config)


@pytest.fixture()
def video_fps(video_processing_obj) -> float:
    data = video_processing_obj.probe_video(test_video_path)
    return video_processing_obj.get_fps_from_probe(data)

async def test_creating_video(video_fps: float, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

    assert video.video_id == 1, "Invalid id"
    assert video.fps == video_fps
    assert test_video_directory / video.source_video_path == test_video_path, "Video paths differ"


async def test_listing_videos(repo: RepositorySQLA):
    uploads = await repo.video_repo.list_all_uploaded_videos_names(test_video_directory)

    assert uploads == [Path(test_video_path.name)]


async def test_getting_multiple_videos(video_fps: float, repo):
    video_list = []
    async with repo.transaction as tr:
        for i in range(200):
            video_list.append(await repo.video_repo.create_new_video(
                video_fps, test_video_directory / f'{i}.mp4'
            ))

    async with repo.transaction:
        videos = await repo.video_repo.get_videos(200)

    assert videos == video_list

    async with repo.transaction:
        videos = await repo.video_repo.get_videos(100)

    assert videos == video_list[:100]

    async with repo.transaction:
        videos = await repo.video_repo.get_videos(10, 10)

    assert videos == video_list[10:20]


async def test_fetching_video(video_fps: float, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

    async with repo.transaction as tr:
        video_fetched = await repo.video_repo.get_video(
            video_id=video.video_id
        )

    assert video_fetched == video


async def test_fetching_non_existing_video(video_fps: float, repo: RepositorySQLA):
    async with repo.transaction as tr:
        assert await repo.video_repo.get_video(video_id=1000) is None


async def test_setting_converted_flag(video_fps: float, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

    async with repo.transaction:
        flagged = await repo.video_repo.set_flag_video_is_converted(
            video.video_id, True, test_video_directory, test_video_path
        )
        assert flagged == True

    async with repo.transaction:
        video_fetched = await repo.video_repo.get_video(
            video_id=video.video_id
        )

    assert Path(video_fetched.converted_video_path) == test_video_path.relative_to(test_video_directory)


async def test_setting_processed_flag(video_fps: float, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

    async with repo.transaction:
        await repo.video_repo.set_flag_video_is_converted(
            video.video_id, True, test_video_directory, test_video_path
        )
        flagged = await repo.video_repo.set_flag_video_is_converted(
            video.video_id, True, test_video_directory, test_video_path
        )
        assert flagged == True

    async with repo.transaction:
        video_fetched = await repo.video_repo.get_video(
            video_id=video.video_id
        )

    assert video_fetched.is_processed == video.is_processed


async def test_setting_corrective_coefficients(video_fps: float, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

    async with repo.transaction:
        await repo.video_repo.adjust_corrective_coefficients(video.video_id, 1.0, 1.0)

    async with repo.transaction:
        video_fetched = await repo.video_repo.get_video(
            video_id=video.video_id
        )

    assert video_fetched.corrective_coefficient_k1 == 1.0
    assert video_fetched.corrective_coefficient_k2 == 1.0


async def test_setting_incorrect_corrective_coefficients(video_fps: float, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

    with pytest.raises(DataIntegrityError):
        async with repo.transaction:
            await repo.video_repo.adjust_corrective_coefficients(video.video_id, 20.0, 1.0)

    with pytest.raises(DataIntegrityError):
        async with repo.transaction:
            await repo.video_repo.adjust_corrective_coefficients(video.video_id, 10.0, 2.5)


async def test_setting_camera_position(video_fps: float, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

    async with repo.transaction:
        await repo.video_repo.set_camera_position(video.video_id, CameraPosition.top_middle_point)

    async with repo.transaction:
        video_fetched = await repo.video_repo.get_video(
            video_id=video.video_id
        )

    assert video_fetched.camera_position == CameraPosition.top_middle_point


async def test_setting_camera_position_with_mistakes(video_fps: float, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

    with pytest.raises(ValueError):
        async with repo.transaction:
            await repo.video_repo.set_camera_position(video.video_id, 100.5) # noqa: testing for error

    with pytest.raises(NotFoundError):
        async with repo.transaction:
            await repo.video_repo.set_camera_position(video.video_id + 100, CameraPosition.top_middle_point)
