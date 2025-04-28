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
                for p in range(10)
            ]
            for _ in frames_numbering
        ]
        await repo.player_data_repo.insert_player_data(
            video.video_id, frames_data
        )

        await tr.commit()

    async with repo.transaction:
        fetched = await repo.player_data_repo.get_tracking_from_frames(video.video_id, 10, 10)

    assert all((frame == [] for frame in fetched.frames[0]))

    async with repo.transaction:
        fetched = await repo.player_data_repo.get_tracking_from_frames(video.video_id, 5, 0)

    assert len(list(filter(len, fetched.frames))) == 5

    async with repo.transaction:
        fetched = await repo.player_data_repo.get_tracking_from_frames(video.video_id, 5, 7)

    assert len(list(filter(len, fetched.frames))) == 3


async def test_get_frames_min_and_max_ids_out_of_range(
    video_fps: float, video_frames_count: int, repo: RepositorySQLA
):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    with pytest.raises(IndexError):
        async with repo.transaction as tr:
            await repo.player_data_repo.get_frames_min_and_max_ids_with_limit_offset(
                video.video_id, 10, 700
            )

    with pytest.raises(IndexError):
        async with repo.transaction as tr:
            await repo.player_data_repo.get_frames_min_and_max_ids_with_limit_offset(
                video.video_id+100, 10, 700
            )


async def test_get_frames_min_and_max_for_not_found_videos(
    repo: RepositorySQLA
):
    with pytest.raises(NotFoundError):
        async with repo.transaction as tr:
            await repo.player_data_repo.get_frames_min_and_max_ids_in_video(100)

async def test_inserting_more_data_than_in_video(
    video_fps: float, video_frames_count: int, repo: RepositorySQLA
):
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


async def test_modifying_player_team(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    frames_numbering = range(0, video_frames_count)

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

    async with repo.transaction as tr:
        await repo.player_data_repo.set_team_to_tracking_id(video.video_id, 5, 0, Team.Away)
        await tr.commit()

    async with repo.transaction:
        fetched = await repo.player_data_repo.get_all_tracking_data(video.video_id)

    for n, frame in enumerate(fetched.frames):
        for point in frame:
            if point.tracking_id == 0:
                assert point.team_id == Team.Away, "Invalid team"


async def test_setting_player_team_to_not_existing(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    frames_numbering = range(0, video_frames_count)

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

    with pytest.raises(NotFoundError):
        async with repo.transaction as tr:
            await repo.player_data_repo.set_team_to_tracking_id(video.video_id, 5, 1000, Team.Away)


async def test_modifying_player_class(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    frames_numbering = range(0, video_frames_count)

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

    async with repo.transaction as tr:
        await repo.player_data_repo.set_player_class_to_tracking_id(
            video.video_id, 5, 0, PlayerClasses.Referee
        )
        await tr.commit()

    async with repo.transaction:
        tr.session.expire_all()
        fetched = await repo.player_data_repo.get_all_tracking_data(video.video_id)

    for n, frame in enumerate(fetched.frames):
        for point in frame:
            if point.tracking_id == 0:
                assert point.class_id == PlayerClasses.Referee, "Invalid player class"


async def test_setting_player_class_to_not_existing(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    frames_numbering = range(0, video_frames_count)

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

    with pytest.raises(NotFoundError):
        async with repo.transaction as tr:
            await repo.player_data_repo.set_player_class_to_tracking_id(
                video.video_id, 5, 1000, PlayerClasses.Referee
            )


async def test_creating_aliases_for_players(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.player_data_repo.create_user_alias_for_players(
            video.video_id, "Hello world"
        )
        await repo.player_data_repo.create_user_alias_for_players(
            video.video_id, "Example", Team.Away
        )
        await repo.player_data_repo.create_user_alias_for_players(
            video.video_id, "Example for home", Team.Home
        )
        await tr.commit()

    async with repo.transaction as tr:
        aliases = await repo.player_data_repo.get_user_alias_for_players(video.video_id)

    assert aliases[1].player_name == "Hello world"
    assert aliases[2].player_name == "Example" and aliases[2].player_team == Team.Away
    assert aliases[3].player_name == "Example for home" and aliases[3].player_team == Team.Home


async def test_deleting_aliases_for_players(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.player_data_repo.create_user_alias_for_players(
            video.video_id, "Hello world"
        )
        await repo.player_data_repo.create_user_alias_for_players(
            video.video_id, "Example", Team.Away
        )
        await repo.player_data_repo.create_user_alias_for_players(
            video.video_id, "Example for home", Team.Home
        )
        await tr.commit()

    async with repo.transaction as tr:
        aliases_deleted = await repo.player_data_repo.delete_player_alias(2)
        assert aliases_deleted, "Not deleted"
        await tr.commit()

    async with repo.transaction as tr:
        aliases = await repo.player_data_repo.get_user_alias_for_players(video.video_id)

    assert aliases[1].player_name == "Hello world"
    assert aliases[3].player_name == "Example for home" and aliases[3].player_team == Team.Home


async def test_deleting_non_existing_alias_for_players(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    with pytest.raises(NotFoundError):
        async with repo.transaction as tr:
            await repo.player_data_repo.delete_player_alias(200)


async def test_editing_aliases_for_players(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.player_data_repo.create_user_alias_for_players(
            video.video_id, "Hello world"
        )
        await repo.player_data_repo.create_user_alias_for_players(
            video.video_id, "Example", Team.Away
        )
        await repo.player_data_repo.create_user_alias_for_players(
            video.video_id, "Example for home", Team.Away
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.player_data_repo.change_player_alias_team(2, Team.Home)
        await repo.player_data_repo.rename_player_alias(3, "Away 33")
        await tr.commit()

    async with repo.transaction as tr:
        aliases = await repo.player_data_repo.get_user_alias_for_players(video.video_id)

    assert aliases[1].player_name == "Hello world" and aliases[1].player_team is None
    assert aliases[2].player_name == "Example" and aliases[2].player_team == Team.Home
    assert aliases[3].player_name == "Away 33" and aliases[3].player_team == Team.Away


async def test_editing_non_existing_aliases_for_players(
    video_fps: float, video_frames_count: int, repo: RepositorySQLA
):
    with pytest.raises(NotFoundError):
        async with repo.transaction as tr:
            await repo.player_data_repo.change_player_alias_team(200, Team.Home)

    with pytest.raises(NotFoundError):
        async with repo.transaction as tr:
            await repo.player_data_repo.rename_player_alias(3, "Away 33")
