from pathlib import Path

from server.algorithms.enums import Team
from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.video_processing import VideoPreprocessingConfig, VideoProcessing
from server.data_storage.dto import BoxDTO
from server.data_storage.dto.relative_point_dto import RelativePointDTO
from server.data_storage.dto.subset_data_input import SubsetDataInputDTO
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


async def test_creating_dataset(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    assert dataset.dataset_id == 1
    assert dataset.subsets == []


async def test_fetching_dataset(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    async with repo.transaction:
        dataset_fetched = await repo.dataset_repo.get_team_dataset_by_id(dataset.dataset_id)

    assert dataset == dataset_fetched


async def test_adding_subset(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    frames_numbering = range(0, 10)

    async with repo.transaction:
        subset_id = await repo.dataset_repo.add_subset_to_dataset(
            dataset.dataset_id,
            frames_numbering.start,
            frames_numbering.stop,
            [
                [
                    SubsetDataInputDTO(
                        tracking_id=p,
                        frame_id=i,
                        class_id=PlayerClasses.Player,
                        team_id=Team.Home,
                        box=BoxDTO(
                            top_point=RelativePointDTO(x=0.2, y=0.2),
                            bottom_point=RelativePointDTO(x=0.35, y=0.4)
                        )
                    )
                    for p in range(10)
                ]
                for i in frames_numbering
            ]
        )

    async with repo.transaction:
        dataset_fetched = await repo.dataset_repo.get_team_dataset_by_id(dataset.dataset_id)

    assert dataset_fetched.subsets[0].subset_id == subset_id


async def test_checking_bounds_of_subset(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    frames_numbering = range(0, 10)

    async with repo.transaction as tr:
        subset_id = await repo.dataset_repo.add_subset_to_dataset(
            dataset.dataset_id,
            frames_numbering.start,
            frames_numbering.stop,
            [
                [
                    SubsetDataInputDTO(
                        tracking_id=p,
                        frame_id=i,
                        class_id=PlayerClasses.Player,
                        team_id=Team.Home,
                        box=BoxDTO(
                            top_point=RelativePointDTO(x=0.2, y=0.2),
                            bottom_point=RelativePointDTO(x=0.35, y=0.4)
                        )
                    )
                    for p in range(10)
                ]
                for i in frames_numbering
            ]
        )
        await tr.commit()

    async with repo.transaction:
        crossover_exists: bool = await repo.dataset_repo.check_frames_crossover_other_subset(
            dataset.dataset_id,
            frames_numbering.start,
            frames_numbering.stop
        )

        assert crossover_exists, "Crossover not found, but must be found"

        crossover_exists = await repo.dataset_repo.check_frames_crossover_other_subset(
            dataset.dataset_id,
            frames_numbering.start,
            frames_numbering.stop-4
        )

        assert crossover_exists, "Crossover not found, but must be found"

        # Check crossover with shift
        crossover_exists = await repo.dataset_repo.check_frames_crossover_other_subset(
            dataset.dataset_id,
            frames_numbering.start + 5,
            frames_numbering.stop
        )

        assert crossover_exists, "Crossover not found, but must be found"

        crossover_exists: bool = await repo.dataset_repo.check_frames_crossover_other_subset(
            dataset.dataset_id,
            frames_numbering.start+100,
            frames_numbering.stop+100
        )

        assert not crossover_exists, "Crossover  found, but must not be found"

        crossover_exists: bool = await repo.dataset_repo.check_frames_crossover_other_subset(
            dataset.dataset_id,
            frames_numbering.start,
            frames_numbering.start
        )

        assert crossover_exists, "Crossover not found, but must be found"


async def test_invalid_crossover_bounds(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    frames_numbering = range(0, 10)

    async with repo.transaction as tr:
        subset_id = await repo.dataset_repo.add_subset_to_dataset(
            dataset.dataset_id,
            frames_numbering.start,
            frames_numbering.stop,
            [
                [
                    SubsetDataInputDTO(
                        tracking_id=p,
                        frame_id=i,
                        class_id=PlayerClasses.Player,
                        team_id=Team.Home,
                        box=BoxDTO(
                            top_point=RelativePointDTO(x=0.2, y=0.2),
                            bottom_point=RelativePointDTO(x=0.35, y=0.4)
                        )
                    )
                    for p in range(10)
                ]
                for i in frames_numbering
            ]
        )
        await tr.commit()

    async with repo.transaction:
        with pytest.raises(ValueError):
            # Checking negative numbers
            await repo.dataset_repo.check_frames_crossover_other_subset(
                dataset.dataset_id,
                frames_numbering.start,
                -1
            )

        with pytest.raises(ValueError):
            # Checking negative numbers
            await repo.dataset_repo.check_frames_crossover_other_subset(
                dataset.dataset_id,
                -1,
                -1
            )
        with pytest.raises(ValueError):
            await repo.dataset_repo.check_frames_crossover_other_subset(
                dataset.dataset_id,
                frames_numbering.stop,
                frames_numbering.start
            )

async def test_adding_subset_to_out_of_bounds(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    frames_numbering = range(video_frames_count+10, video_frames_count+20)
    with pytest.raises(ValueError):
        async with repo.transaction:
            subset_id = await repo.dataset_repo.add_subset_to_dataset(
                dataset.dataset_id,
                frames_numbering.start,
                frames_numbering.stop,
                [
                    [
                        SubsetDataInputDTO(
                            tracking_id=p,
                            frame_id=i,
                            class_id=PlayerClasses.Player,
                            team_id=Team.Home,
                            box=BoxDTO(
                                top_point=RelativePointDTO(x=0.2, y=0.2),
                                bottom_point=RelativePointDTO(x=0.35, y=0.4)
                            )
                        )
                        for p in range(10)
                    ]
                    for i in frames_numbering
                ]
            )


async def test_adding_subset_to_invalid_boundaries(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    frames_numbering = range(10, 20)
    with pytest.raises(ValueError):
        async with repo.transaction:
            subset_id = await repo.dataset_repo.add_subset_to_dataset(
                dataset.dataset_id,
                100,
                20,
                [
                    [
                        SubsetDataInputDTO(
                            tracking_id=p,
                            frame_id=i,
                            class_id=PlayerClasses.Player,
                            team_id=Team.Home,
                            box=BoxDTO(
                                top_point=RelativePointDTO(x=0.2, y=0.2),
                                bottom_point=RelativePointDTO(x=0.35, y=0.4)
                            )
                        )
                        for p in range(10)
                    ]
                    for i in frames_numbering
                ]
            )


async def test_adding_subset_with_duplicates(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    frames_numbering = range(video_frames_count+10, video_frames_count+20)
    with pytest.raises(DataIntegrityError):
        async with repo.transaction:
            subset_id = await repo.dataset_repo.add_subset_to_dataset(
                dataset.dataset_id,
                frames_numbering.start,
                frames_numbering.stop,
                [
                    [
                        SubsetDataInputDTO(
                            tracking_id=100,
                            frame_id=i,
                            class_id=PlayerClasses.Player,
                            team_id=Team.Home,
                            box=BoxDTO(
                                top_point=RelativePointDTO(x=0.2, y=0.2),
                                bottom_point=RelativePointDTO(x=0.35, y=0.4)
                            )
                        )
                        for _ in range(10)
                    ]
                    for i in frames_numbering
                ]
            )


async def test_adding_subset_to_not_existing_dataset(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    frames_numbering = range(video_frames_count+10, video_frames_count+20)
    with pytest.raises(NotFoundError):
        async with repo.transaction:
            subset_id = await repo.dataset_repo.add_subset_to_dataset(
                100,
                frames_numbering.start,
                frames_numbering.stop,
                [
                    [
                        SubsetDataInputDTO(
                            tracking_id=100,
                            frame_id=i,
                            class_id=PlayerClasses.Player,
                            team_id=Team.Home,
                            box=BoxDTO(
                                top_point=RelativePointDTO(x=0.2, y=0.2),
                                bottom_point=RelativePointDTO(x=0.35, y=0.4)
                            )
                        )
                        for _ in range(10)
                    ]
                    for i in frames_numbering
                ]
            )


async def test_changing_team_for_player(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    frames_numbering = range(0, 10)

    async with repo.transaction as tr:
        subset_id = await repo.dataset_repo.add_subset_to_dataset(
            dataset.dataset_id,
            frames_numbering.start,
            frames_numbering.stop,
            [
                [
                    SubsetDataInputDTO(
                        tracking_id=p,
                        frame_id=i,
                        class_id=PlayerClasses.Player,
                        team_id=Team.Home,
                        box=BoxDTO(
                            top_point=RelativePointDTO(x=0.2, y=0.2),
                            bottom_point=RelativePointDTO(x=0.35, y=0.4)
                        )
                    )
                    for p in range(10)
                ]
                for i in frames_numbering
            ]
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.dataset_repo.set_player_team(subset_id, 0, Team.Away)
        await tr.commit()

    async with repo.transaction:
        dataset_fetched = await repo.dataset_repo.get_team_dataset_by_id(dataset.dataset_id)

    assert all(
        (
            player_data.team_id == Team.Away
            for player_data in filter(lambda v: v.tracking_id == 0, dataset_fetched.subsets[0].subset_data)
        )
    )


async def test_changing_team_for_non_existing_player(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    frames_numbering = range(0, 10)

    async with repo.transaction as tr:
        subset_id = await repo.dataset_repo.add_subset_to_dataset(
            dataset.dataset_id,
            frames_numbering.start,
            frames_numbering.stop,
            [
                [
                    SubsetDataInputDTO(
                        tracking_id=p,
                        frame_id=i,
                        class_id=PlayerClasses.Player,
                        team_id=Team.Home,
                        box=BoxDTO(
                            top_point=RelativePointDTO(x=0.2, y=0.2),
                            bottom_point=RelativePointDTO(x=0.35, y=0.4)
                        )
                    )
                    for p in range(10)
                ]
                for i in frames_numbering
            ]
        )
        await tr.commit()

    with pytest.raises(NotFoundError):
        async with repo.transaction as tr:
            await repo.dataset_repo.set_player_team(subset_id, 100, Team.Away)
            await tr.commit()


async def test_getting_teams_data_points_count(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    frames_numbering = range(0, 10)

    async with repo.transaction as tr:
        subset_id = await repo.dataset_repo.add_subset_to_dataset(
            dataset.dataset_id,
            frames_numbering.start,
            frames_numbering.stop,
            [
                [
                    SubsetDataInputDTO(
                        tracking_id=p,
                        frame_id=i,
                        class_id=PlayerClasses.Player,
                        team_id=Team.Home,
                        box=BoxDTO(
                            top_point=RelativePointDTO(x=0.2, y=0.2),
                            bottom_point=RelativePointDTO(x=0.35, y=0.4)
                        )
                    )
                    for p in range(10)
                ]
                for i in frames_numbering
            ]
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.dataset_repo.set_player_team(subset_id, 0, Team.Away)
        await tr.commit()

    async with repo.transaction:
        teams_sizes = await repo.dataset_repo.get_teams_dataset_size(dataset.dataset_id)

    assert teams_sizes == {Team.Home: 9*len(frames_numbering), Team.Away: len(frames_numbering)}


async def test_points_count_from_many_subsets(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    for subset_n in range(10):
        frames_numbering = range(subset_n+0, subset_n+10)
        async with repo.transaction as tr:
            subset_id = await repo.dataset_repo.add_subset_to_dataset(
                dataset.dataset_id,
                frames_numbering.start,
                frames_numbering.stop,
                [
                    [
                        SubsetDataInputDTO(
                            tracking_id=p,
                            frame_id=i,
                            class_id=PlayerClasses.Player,
                            team_id=Team.Home,
                            box=BoxDTO(
                                top_point=RelativePointDTO(x=0.2, y=0.2),
                                bottom_point=RelativePointDTO(x=0.35, y=0.4)
                            )
                        )
                        for p in range(10)
                    ]
                    for i in frames_numbering
                ]
            )
            await tr.commit()

    async with repo.transaction as tr:
        await repo.dataset_repo.set_player_team(subset_id, 0, Team.Away)
        await tr.commit()

    async with repo.transaction:
        teams_sizes = await repo.dataset_repo.get_teams_dataset_size(dataset.dataset_id)

    assert teams_sizes == {Team.Home: 990, Team.Away: 10}


async def test_changing_player_class(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.frames_repo.create_frames(1, video_frames_count)
        await tr.commit()

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    frames_numbering = range(0, 10)

    async with repo.transaction as tr:
        subset_id = await repo.dataset_repo.add_subset_to_dataset(
            dataset.dataset_id,
            frames_numbering.start,
            frames_numbering.stop,
            [
                [
                    SubsetDataInputDTO(
                        tracking_id=p,
                        frame_id=i,
                        class_id=PlayerClasses.Player,
                        team_id=Team.Home,
                        box=BoxDTO(
                            top_point=RelativePointDTO(x=0.2, y=0.2),
                            bottom_point=RelativePointDTO(x=0.35, y=0.4)
                        )
                    )
                    for p in range(10)
                ]
                for i in frames_numbering
            ]
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.dataset_repo.set_player_class(subset_id, 0, PlayerClasses.Goalie)
        await tr.commit()

    async with repo.transaction:
        dataset_fetched = await repo.dataset_repo.get_team_dataset_by_id(dataset.dataset_id)

    assert all(
        (
            player_data.class_id == PlayerClasses.Goalie
            for player_data in filter(lambda v: v.tracking_id == 0, dataset_fetched.subsets[0].subset_data)
        )
    )


async def test_changing_player_class_for_non_existing_player(
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

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    frames_numbering = range(0, 10)

    async with repo.transaction as tr:
        subset_id = await repo.dataset_repo.add_subset_to_dataset(
            dataset.dataset_id,
            frames_numbering.start,
            frames_numbering.stop,
            [
                [
                    SubsetDataInputDTO(
                        tracking_id=p,
                        frame_id=i,
                        class_id=PlayerClasses.Player,
                        team_id=Team.Home,
                        box=BoxDTO(
                            top_point=RelativePointDTO(x=0.2, y=0.2),
                            bottom_point=RelativePointDTO(x=0.35, y=0.4)
                        )
                    )
                    for p in range(10)
                ]
                for i in frames_numbering
            ]
        )
        await tr.commit()

    with pytest.raises(NotFoundError):
        async with repo.transaction as tr:
            await repo.dataset_repo.set_player_class(subset_id, 100, PlayerClasses.Goalie)
            await tr.commit()

async def test_getting_teams_data_points_count_with_class_change(
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

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    frames_numbering = range(0, 10)

    async with repo.transaction as tr:
        subset_id = await repo.dataset_repo.add_subset_to_dataset(
            dataset.dataset_id,
            frames_numbering.start,
            frames_numbering.stop,
            [
                [
                    SubsetDataInputDTO(
                        tracking_id=p,
                        frame_id=i,
                        class_id=PlayerClasses.Player,
                        team_id=Team.Home,
                        box=BoxDTO(
                            top_point=RelativePointDTO(x=0.2, y=0.2),
                            bottom_point=RelativePointDTO(x=0.35, y=0.4)
                        )
                    )
                    for p in range(10)
                ]
                for i in frames_numbering
            ]
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.dataset_repo.set_player_class(subset_id, 0, PlayerClasses.Referee)
        await tr.commit()

    async with repo.transaction:
        teams_sizes = await repo.dataset_repo.get_teams_dataset_size(dataset.dataset_id)

    assert teams_sizes == {Team.Home: 9*len(frames_numbering), Team.Away: 0}

async def test_killing_tracking(
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

    async with repo.transaction as tr:
        dataset = await repo.dataset_repo.create_dataset_for_video(video.video_id)
        await tr.commit()

    frames_numbering = range(0, 10)

    async with repo.transaction as tr:
        subset_id = await repo.dataset_repo.add_subset_to_dataset(
            dataset.dataset_id,
            frames_numbering.start,
            frames_numbering.stop,
            [
                [
                    SubsetDataInputDTO(
                        tracking_id=p,
                        frame_id=i,
                        class_id=PlayerClasses.Player,
                        team_id=Team.Home,
                        box=BoxDTO(
                            top_point=RelativePointDTO(x=0.2, y=0.2),
                            bottom_point=RelativePointDTO(x=0.35, y=0.4)
                        )
                    )
                    for p in range(10)
                ]
                for i in frames_numbering
            ]
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.dataset_repo.set_player_team(subset_id, 0, Team.Away)
        await tr.commit()

    async with repo.transaction as tr:
        killed_amount = await repo.dataset_repo.kill_tracking(
            subset_id, 0, 5
        )
        await tr.commit()
        # If not expired - error will occur since relationship fetch is cached, but deleted by query
        tr.session.expire_all()

    async with repo.transaction:
        teams_sizes = await repo.dataset_repo.get_teams_dataset_size(dataset.dataset_id)

    assert teams_sizes == {Team.Home: 9*len(frames_numbering), Team.Away: len(frames_numbering)-killed_amount}

    async with repo.transaction:
        dataset_fetched = await repo.dataset_repo.get_team_dataset_by_id(dataset.dataset_id)

    assert len(
        [
            player_data
            for player_data in filter(lambda v: v.tracking_id == 0, dataset_fetched.subsets[0].subset_data)
        ]
    ) == 5

