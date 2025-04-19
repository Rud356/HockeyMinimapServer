import time
from pathlib import Path

from server.algorithms.enums import Team
from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.video_processing import VideoPreprocessingConfig, VideoProcessing
from server.data_storage.dto import BoxDTO, PointDTO
from server.data_storage.dto.player_data_dto import PlayerDataDTO
from server.data_storage.exceptions import DataIntegrityError, NotFoundError
from .fixtures import *

test_video_directory: Path = Path(__file__).parent.parent / "videos"
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


async def test_creating_player_data(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    frames_numbering = range(0, 10)
    async with repo.transaction as tr:
        frames_data = [
            [
                PlayerDataDTO(
                    tracking_id=p,
                    team_id=Team.Home,
                    player_id=None,
                    player_name=None,
                    class_id=PlayerClasses.Player,
                    player_on_minimap=PointDTO(x=0.35, y=0.3),
                    player_on_camera=BoxDTO(
                        top_point=PointDTO(x=0.2, y=0.2),
                        bottom_point=PointDTO(x=0.35, y=0.4)
                    )
                )
                for p in range(10)
            ]
            for _ in frames_numbering
        ]
        await repo.player_data_repo.insert_player_data(
            video.video_id, frames_data
        )

        await tr.commit()


async def test_fetching_all_player_data(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    frames_numbering = range(0, 10)
    async with repo.transaction as tr:
        frames_data = [
            [
                PlayerDataDTO(
                    tracking_id=p,
                    team_id=Team.Home,
                    player_id=None,
                    player_name=None,
                    class_id=PlayerClasses.Player,
                    player_on_minimap=PointDTO(x=0.35, y=0.3),
                    player_on_camera=BoxDTO(
                        top_point=PointDTO(x=0.2, y=0.2),
                        bottom_point=PointDTO(x=0.35, y=0.4)
                    )
                )
                for p in range(10)
            ]
            for _ in frames_numbering
        ]
        await repo.player_data_repo.insert_player_data(
            video.video_id, frames_data
        )

        await tr.commit()

    async with repo.transaction:
        fetched = await repo.player_data_repo.get_all_tracking_data(video.video_id)

    assert len(list(filter(len, fetched.frames))) == len(frames_data)


async def test_inserting_more_data_than_in_video(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    frames_numbering = range(0, 1000)
    async with repo.transaction as tr:
        frames_data = [
            [
                PlayerDataDTO(
                    tracking_id=p,
                    team_id=Team.Home,
                    player_id=None,
                    player_name=None,
                    class_id=PlayerClasses.Player,
                    player_on_minimap=PointDTO(x=0.35, y=0.3),
                    player_on_camera=BoxDTO(
                        top_point=PointDTO(x=0.2, y=0.2),
                        bottom_point=PointDTO(x=0.35, y=0.4)
                    )
                )
                for p in range(10)
            ]
            for _ in frames_numbering
        ]
        with pytest.raises(NotFoundError):
            await repo.player_data_repo.insert_player_data(
                video.video_id, frames_data
            )

        await tr.commit()


async def test_inserting_invalid_data(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    frames_numbering = range(0, 100)
    async with repo.transaction as tr:
        frames_data = [
            [
                PlayerDataDTO(
                    tracking_id=p,
                    team_id=Team.Home,
                    player_id=None,
                    player_name=None,
                    class_id=PlayerClasses.Player,
                    # Invalid data, points must have values between 0 and 1
                    player_on_minimap=PointDTO(x=1.35, y=0.3),
                    player_on_camera=BoxDTO(
                        top_point=PointDTO(x=0.2, y=0.2),
                        bottom_point=PointDTO(x=0.35, y=0.4)
                    )
                )
                for p in range(10)
            ]
            for _ in frames_numbering
        ]
        with pytest.raises(DataIntegrityError):
            await repo.player_data_repo.insert_player_data(
                video.video_id, frames_data
            )

        await tr.commit()


async def test_fetching_partial_player_data(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    frames_numbering = range(0, 10)
    async with repo.transaction as tr:
        frames_data = [
            [
                PlayerDataDTO(
                    tracking_id=p,
                    team_id=Team.Home,
                    player_id=None,
                    player_name=None,
                    class_id=PlayerClasses.Player,
                    player_on_minimap=PointDTO(x=0.35, y=0.3),
                    player_on_camera=BoxDTO(
                        top_point=PointDTO(x=0.2, y=0.2),
                        bottom_point=PointDTO(x=0.35, y=0.4)
                    )
                )
                for p in range(100)
            ]
            for _ in frames_numbering
        ]
        await repo.player_data_repo.insert_player_data(
            video.video_id, frames_data
        )

        await tr.commit()

    async with repo.transaction:
        fetched = await repo.player_data_repo.get_all_tracking_data(video.video_id)

    assert len(list(filter(len, fetched.frames))) == len(frames_data)


async def test_modifying_player_team(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    frames_numbering = range(0, video_frames_count*10)

    async with repo.transaction as tr:
        frames_data = [
            [
                PlayerDataDTO(
                    tracking_id=p,
                    team_id=Team.Home,
                    player_id=None,
                    player_name=None,
                    class_id=PlayerClasses.Player,
                    player_on_minimap=PointDTO(x=0.35, y=0.3),
                    player_on_camera=BoxDTO(
                        top_point=PointDTO(x=0.2, y=0.2),
                        bottom_point=PointDTO(x=0.35, y=0.4)
                    )
                )
                for p in range(10)
            ]
            for _ in frames_numbering
        ]
        start = time.time()
        await repo.player_data_repo.insert_player_data(
            video.video_id, frames_data
        )
        await tr.commit()
        print(f"{time.time() - start}s to finish")
