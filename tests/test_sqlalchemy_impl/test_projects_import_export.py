from pathlib import Path

from server.algorithms.enums import Team
from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.video_processing import VideoPreprocessingConfig, VideoProcessing
from server.data_storage.dto import BoxDTO, DatasetDTO, FrameDataDTO, MinimapDataDTO
from server.data_storage.dto.relative_point_dto import RelativePointDTO
from server.data_storage.dto.subset_data_input import SubsetDataInputDTO
from .fixtures import *

static: Path = Path(__file__).parent.parent
test_video_directory: Path = static / "videos"
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


async def test_export_data_about_project(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.video_repo.set_flag_video_is_converted(
            video.video_id,
            True,
            test_video_directory,
            test_video_path
        )
        await repo.video_repo.set_flag_video_is_processed(
            video.video_id,
            True
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
        video = await repo.video_repo.get_video(video.video_id)
        await repo.dataset_repo.add_subset_to_dataset(
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

    point_src = {
        RelativePointDTO(x=0.5, y=0.5): RelativePointDTO(x=0.5, y=0.5),
        RelativePointDTO(x=0.56, y=0.56): RelativePointDTO(x=0.54, y=0.52),
        RelativePointDTO(x=0.6, y=0.6): RelativePointDTO(x=0.7, y=0.2),
        RelativePointDTO(x=0.26, y=0.2): RelativePointDTO(x=0.2, y=0.17)
    }
    async with repo.transaction as tr:
        await repo.map_data_repo.create_point_mapping_for_video(
            video_id=video.video_id, mapping=point_src
        )

        await tr.commit()

    async with repo.transaction as tr:
        project = await repo.project_repo.create_project(
            for_video_id=video.video_id,
            name="Hello world!",
            team_home_name="Home1",
            team_away_name="Away1"
        )
        await tr.commit()

    async with repo.transaction:
        project_data = await repo.export_project_data(project.project_id)

    assert project_data.video_data == video
    assert project_data.project_header == project
    assert all(
        [
            map_fetched.point_on_minimap == map_src and map_fetched.point_on_camera == video_src
                for map_fetched, (map_src, video_src) in zip(project_data.minimap_data, point_src.items())
        ]
    )

async def test_project_import(video_fps: float, video_frames_count: int, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )
        await tr.commit()

    async with repo.transaction as tr:
        await repo.video_repo.set_flag_video_is_converted(
            video.video_id,
            True,
            test_video_directory,
            test_video_path
        )
        await repo.video_repo.set_flag_video_is_processed(
            video.video_id,
            True
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
        video = await repo.video_repo.get_video(video.video_id)
        await repo.dataset_repo.add_subset_to_dataset(
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

    point_src = {
        RelativePointDTO(x=0.5, y=0.5): RelativePointDTO(x=0.5, y=0.5),
        RelativePointDTO(x=0.56, y=0.56): RelativePointDTO(x=0.54, y=0.52),
        RelativePointDTO(x=0.6, y=0.6): RelativePointDTO(x=0.7, y=0.2),
        RelativePointDTO(x=0.26, y=0.2): RelativePointDTO(x=0.2, y=0.17)
    }
    async with repo.transaction as tr:
        await repo.map_data_repo.create_point_mapping_for_video(
            video_id=video.video_id, mapping=point_src
        )
        original_mapping = await repo.map_data_repo.get_points_mapping_for_video(
            video_id=video.video_id
        )
        await tr.commit()

    async with repo.transaction as tr:
        project = await repo.project_repo.create_project(
            for_video_id=video.video_id,
            name="Hello world!",
            team_home_name="Home1",
            team_away_name="Away1"
        )
        await tr.commit()

    async with repo.transaction:
        project_data = await repo.export_project_data(project.project_id)

    assert project_data.video_data == video
    assert project_data.project_header == project
    assert all(
        [
            map_fetched.point_on_minimap == map_src and map_fetched.point_on_camera == video_src
                for map_fetched, (map_src, video_src) in zip(project_data.minimap_data, point_src.items())
        ]
    )

    async with repo.transaction as tr:
        new_project = await repo.import_project_data(
            static,
            static / "videos",
            project_data
        )
        new_video = await repo.video_repo.get_video(new_project.for_video_id)
        minimap_data: list[
            MinimapDataDTO
        ] = await repo.map_data_repo.get_points_mapping_for_video(
            new_video.video_id
        )
        frame_data: FrameDataDTO = await repo.player_data_repo.get_all_tracking_data(
            new_video.video_id
        )
        teams_dataset: DatasetDTO = await repo.dataset_repo.get_team_dataset_by_id(
            new_video.dataset_id
        )
        await tr.commit()

    for minimap_point, original_map in zip(minimap_data, original_mapping):
        # Reset id for checkups
        assert minimap_point.map_data_id != original_map.map_data_id
        minimap_point.map_data_id = 0
        original_map.map_data_id = 0

    assert new_project.name == project.name
    assert new_project.team_home_name == project.team_home_name
    assert new_project.team_away_name == project.team_away_name
    assert new_project.for_video_id != project.for_video_id

    assert minimap_data == original_mapping
    assert Path(test_video_directory.name) / video.source_video_path == Path(new_video.source_video_path)
    assert Path(test_video_directory.name) / video.converted_video_path == Path(new_video.converted_video_path)
    assert video.corrective_coefficient_k1 == new_video.corrective_coefficient_k1
    assert video.corrective_coefficient_k2 == new_video.corrective_coefficient_k2
    assert video.fps == new_video.fps

    assert frame_data == project_data.frame_data
    assert new_video.dataset_id is not None
    assert video.dataset_id != new_video.dataset_id

    # Prepare testing by erasing ids and ensuring they are not equal
    assert project_data.teams_dataset.dataset_id != teams_dataset.dataset_id
    project_data.teams_dataset.dataset_id = 0
    teams_dataset.dataset_id = 0

    for subset_a, subset_b in zip(project_data.teams_dataset.subsets, teams_dataset.subsets):
        assert subset_a.subset_id != subset_b.subset_id
        subset_a.subset_id = 0
        subset_b.subset_id = 0

        for subset_data_a, subset_data_b in zip(subset_a.subset_data, subset_b.subset_data):
            assert subset_data_a.subset_id != subset_data_b.subset_id
            subset_data_a.subset_id = 0
            subset_data_b.subset_id = 0

    assert project_data.teams_dataset.subsets == teams_dataset.subsets
