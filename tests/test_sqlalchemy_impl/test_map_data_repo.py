from pathlib import Path

from sqlalchemy import Select, func

from server.algorithms.video_processing import VideoPreprocessingConfig, VideoProcessing
from server.data_storage.dto import PointDTO
from server.data_storage.dto.relative_point_dto import RelativePointDTO
from server.data_storage.exceptions import DataIntegrityError, NotFoundError
from server.data_storage.sql_implementation.tables import MapData, Point
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
def video_probe_data(video_processing_obj) -> dict[str, str]:
    return video_processing_obj.probe_video(test_video_path)


@pytest.fixture()
def video_fps(video_processing_obj, video_probe_data) -> float:
    return video_processing_obj.get_fps_from_probe(video_probe_data)


async def test_creating_map_data(video_fps: float, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

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
        points_inserted = await tr.session.scalar(
            Select(func.count("*")).where(MapData.video_id == video.video_id)
        )

    assert points_inserted == len(point_src)


async def test_getting_multiple_points(video_fps: float, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

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
        mapped_points = await repo.map_data_repo.get_points_mapping_for_video(video.video_id)

    assert {
        RelativePointDTO(x=point.point_on_minimap.x, y=point.point_on_minimap.y):
            RelativePointDTO(x=point.point_on_camera.x, y=point.point_on_camera.y)
        for point in mapped_points
    } == point_src, "Mismatch points"


async def test_deleting_points(video_fps: float, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

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

    async with repo.transaction as tr:
        dropped_count = await repo.map_data_repo.drop_all_mapping_points_for_video(video.video_id)
        await tr.commit()

    assert dropped_count == len(point_src)

    async with repo.transaction as tr:
        result_points = (await tr.session.scalars(
            Select(Point)
        )).all()

    assert len(result_points) == 0


async def test_editing_points(video_fps: float, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

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

    async with repo.transaction as tr:
        await repo.map_data_repo.edit_point_from_mapping(
            1, is_used=False
        )

    async with repo.transaction as tr:
        mapped_points = await repo.map_data_repo.get_points_mapping_for_video(video.video_id)

    assert [point.is_used for point in mapped_points] == [False, True, True, True], "Mismatch points data"

    async with repo.transaction as tr:
        await repo.map_data_repo.edit_point_from_mapping(
            2, point_on_minimap=PointDTO(x=0.1, y=0.1)
        )

    async with repo.transaction as tr:
        mapped_points = await repo.map_data_repo.get_points_mapping_for_video(video.video_id)

    assert mapped_points[1].point_on_minimap == RelativePointDTO(x=0.1, y=0.1)

    async with repo.transaction as tr:
        await repo.map_data_repo.edit_point_from_mapping(
            3, point_on_camera=PointDTO(x=0.25, y=0.25)
        )

    async with repo.transaction as tr:
        mapped_points = await repo.map_data_repo.get_points_mapping_for_video(video.video_id)

    assert mapped_points[2].point_on_camera == RelativePointDTO(x=0.25, y=0.25)


async def test_editing_not_existing_points(video_fps: float, repo: RepositorySQLA):
    with pytest.raises(NotFoundError):
        async with repo.transaction as tr:
            await repo.map_data_repo.edit_point_from_mapping(
                1, is_used=False
            )


async def test_editing_points_with_invalid_points(video_fps: float, repo: RepositorySQLA):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

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

    with pytest.raises(DataIntegrityError):
        async with repo.transaction as tr:
            await repo.map_data_repo.edit_point_from_mapping(
                2, point_on_minimap=PointDTO(x=1.1, y=1.1)
            )

    with pytest.raises(DataIntegrityError):
        async with repo.transaction as tr:
            await repo.map_data_repo.edit_point_from_mapping(
                2, point_on_minimap=PointDTO(x=-0.1, y=-0.1)
            )

    with pytest.raises(DataIntegrityError):
        async with repo.transaction as tr:
            await repo.map_data_repo.edit_point_from_mapping(
                2, point_on_camera=PointDTO(x=1.1, y=1.1)
            )

    with pytest.raises(DataIntegrityError):
        async with repo.transaction as tr:
            await repo.map_data_repo.edit_point_from_mapping(
                2, point_on_camera=PointDTO(x=-0.1, y=-0.1)
            )
