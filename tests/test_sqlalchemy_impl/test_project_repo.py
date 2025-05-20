import datetime
from pathlib import Path

from server.algorithms.video_processing import VideoPreprocessingConfig, VideoProcessing
from server.data_storage.dto import ProjectDTO
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


async def test_creating_project(video_fps: float, repo):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

    project_metadata = ProjectDTO(
        project_id=1,
        for_video_id=video.video_id,
        name="Hello world!",
        created_at=datetime.datetime.now(),
        team_home_name="Home1",
        team_away_name="Away1"
    )

    async with repo.transaction as tr:
        project = await repo.project_repo.create_project(
            for_video_id=video.video_id,
            name="Hello world!",
            team_home_name="Home1",
            team_away_name="Away1"
        )
        await tr.commit()

    project_metadata.created_at = project.created_at
    assert project_metadata == project


async def test_creating_project_with_defaults(video_fps: float, repo):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

    project_metadata = ProjectDTO(
        project_id=1,
        for_video_id=video.video_id,
        name="Hello world!",
        created_at=datetime.datetime.now(),
        team_home_name="Home",
        team_away_name="Away"
    )

    async with repo.transaction as tr:
        project = await repo.project_repo.create_project(
            for_video_id=video.video_id,
            name="Hello world!",
        )

    project_metadata.created_at = project.created_at
    assert project_metadata == project


async def test_fetching_project(video_fps: float, repo):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

    project_metadata = ProjectDTO(
        project_id=1,
        for_video_id=video.video_id,
        name="Hello world!",
        created_at=datetime.datetime.now(),
        team_home_name="Home",
        team_away_name="Away"
    )

    async with repo.transaction as tr:
        project = await repo.project_repo.create_project(
            for_video_id=video.video_id,
            name="Hello world!",
        )

    async with repo.transaction as tr:
        project_fetched = await repo.project_repo.get_project(project.project_id)

    assert project_fetched == project


async def test_fetching_multiple_projects(video_fps: float, repo):
    async with repo.transaction as tr:
        video = await repo.video_repo.create_new_video(
            video_fps, test_video_path.relative_to(test_video_directory)
        )

    projects: list[ProjectDTO] = []
    async with repo.transaction as tr:
        for i in range(100):
            project = await repo.project_repo.create_project(
                for_video_id=video.video_id,
                name=f"Hello world {i}!",
            )
            projects.append(project)

    async with repo.transaction as tr:
        projects_fetched = await repo.project_repo.get_projects()

    assert projects_fetched == projects

    async with repo.transaction as tr:
        projects_fetched = await repo.project_repo.get_projects(limit=20)

    assert projects_fetched == projects[:20]

    async with repo.transaction as tr:
        projects_fetched = await repo.project_repo.get_projects(limit=20, offset=20)

    assert projects_fetched == projects[20:40]

