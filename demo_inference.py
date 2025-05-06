import asyncio
import os
import time
import typing
from concurrent.futures.thread import ThreadPoolExecutor
from pathlib import Path
from typing import AsyncGenerator, Optional

import cv2
import numpy
import torch
from torchvision import datasets

from server import config_data, server
from server.algorithms.data_types import BoundingBox, CV_Image, Point, RelativePoint
from server.algorithms.data_types.field_extracted_data import FieldExtractedData
from server.algorithms.enums import CameraPosition, Team
from server.algorithms.key_point_placer import KeyPointPlacer
from server.algorithms.nn import TeamDetectionPredictor, TeamDetectorModel, TeamDetectorTeacher, team_detector_transform
from server.algorithms.player_tracker import PlayerTracker
from server.algorithms.players_mapper import PlayersMapper
from server.algorithms.services.field_data_extraction_service import FieldDataExtractionService
from server.algorithms.services.field_predictor_service import FieldPredictorService
from server.algorithms.services.map_video_renderer_service import MapVideoRendererService
from server.algorithms.services.player_data_extraction_service import PlayerDataExtractionService
from server.algorithms.video_processing import VideoProcessing
from server.data_storage.dto import BoxDTO
from server.data_storage.dto.player_data_dto import PlayerDataDTO
from server.data_storage.dto.relative_point_dto import RelativePointDTO
from server.utils.async_buffered_generator import buffered_generator
from server.utils.async_video_reader import async_video_reader
from server.utils.config import VideoPreprocessingConfig
from server.views.map_view import MapView

MINIMAP_KEY_POINTS = config_data.minimap_config
torch.set_float32_matmul_precision('medium')
os.environ["OPENCV_VIDEO_ACCELERATION"] = "ANY"
source_video: Path = Path("tests/videos/converted_demo.mp4")

classes_names = list(Team.__members__)
test_dir = 'datasets/custom_validation'
data_dir = 'datasets/custom_dataset'

train_dataset = datasets.ImageFolder(os.path.join(data_dir, 'train'), transform=team_detector_transform)
val_dataset = datasets.ImageFolder(os.path.join(data_dir, 'val'), transform=team_detector_transform)
print(Path(os.path.join(data_dir, 'train')).resolve(), Path(os.path.join(data_dir, 'val')).resolve())

device = "cuda" if torch.cuda.is_available() else "cpu"
trainer = TeamDetectorTeacher(train_dataset, val_dataset, 100, TeamDetectorModel(), device)
model = trainer.train_nn()
predictor: TeamDetectionPredictor = TeamDetectionPredictor(model, team_detector_transform, device)

for image_name in os.listdir(test_dir):
    image_path = os.path.join(test_dir, image_name)
    if os.path.isfile(image_path):
        img: CV_Image = typing.cast(CV_Image, cv2.imread(image_path))
        predicted_team: Team = predictor(img)
        print(f'Image {image_name}: The player belongs to {predicted_team.name} team')


def draw_text(img, text, pos, color):
    return cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 2, cv2.LINE_AA)

async def field_data(
    frame: numpy.ndarray,
    field_service: FieldPredictorService,
    key_point_placer: KeyPointPlacer
) -> FieldExtractedData:
    fut = await field_service.add_inference_task_to_queue(frame)
    inference = (await fut)[0].to("cpu")
    field_points = FieldDataExtractionService(key_point_placer).get_field_data(
        inference
    )

    return field_points


async def main(video_path: Path):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    map_view = MapView(object()) # noqa: repository isn't used here

    field_service = server.field_predictor
    player_service = server.player_predictor

    loop = asyncio.get_running_loop()
    loop.create_task(field_service())
    loop.create_task(player_service())

    relative_map_points = map_view.get_relative_minimap_points(MINIMAP_KEY_POINTS)
    key_points_mapping, mask = await map_view.get_key_points_from_video(
        video_path,
        CameraPosition.top_middle_point,
        MINIMAP_KEY_POINTS,
        VideoProcessing(config_data.video_processing),
        field_service,
        3.0
    )


    # DEMO RESOLUTION, FIGURED OUT IN RUNTIME
    key_point_placer = KeyPointPlacer(MINIMAP_KEY_POINTS, CameraPosition.top_middle_point, (1280, 720))
    team_predictor: TeamDetectionPredictor = predictor

    map_img = cv2.imread("static/map.png")
    # Video output streams
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_video = cv2.VideoWriter('output.mp4', fourcc, 25.0, (1280, 720))
    map_bbox: BoundingBox = BoundingBox(
        Point(MINIMAP_KEY_POINTS.top_left_field_point.x, MINIMAP_KEY_POINTS.top_left_field_point.y),
        Point(MINIMAP_KEY_POINTS.bottom_right_field_point.x, MINIMAP_KEY_POINTS.bottom_right_field_point.y)
    )

    video_render_service = MapVideoRendererService(
        ThreadPoolExecutor(1),
        25.0,
        Path('output_map.mp4'),
        map_bbox,
        map_img,
        video_processing_config=VideoPreprocessingConfig(video_width=1280, video_height=720, crf=24)
    )
    data_renderer: AsyncGenerator[int, list[PlayerDataDTO] | None] = video_render_service.data_renderer()
    await data_renderer.asend(None)

    renderer_task = loop.create_task(video_render_service.run())

    cap = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)
    frame_n = 0
    mapper: Optional[PlayersMapper] = None
    player_data_extractor: Optional[PlayerDataExtractionService] = None
    width: int
    height: int
    resolution: tuple[int, int] = (1280, 720)

    RELATIVE_MAP_BBOX = BoundingBox(Point(0, 0), Point(1, 1))

    async for frame in buffered_generator(async_video_reader(cap), 30):
        if frame_n == 0:
            height, width, _ = frame.shape
            resolution = (width, height)

            # Update blue line bottom position
            blue_line_bottom_rel = Point(x=423, y=280).to_relative_coordinates_inside_bbox(map_bbox)
            blue_line_bottom_new = RelativePointDTO(
                x=blue_line_bottom_rel.x,
                y=blue_line_bottom_rel.y
            )
            was_point = RelativePointDTO(
                x=relative_map_points.left_blue_line_top.x,
                y=relative_map_points.left_blue_line_top.y
            )
            key_points_mapping[blue_line_bottom_new] = key_points_mapping.pop(was_point)

            # Move goal line position
            goal_line_bottom_rel = Point(x=1162, y=163).to_relative_coordinates_inside_bbox(map_bbox)
            goal_line_bottom = RelativePointDTO(
                x=goal_line_bottom_rel.x,
                y=goal_line_bottom_rel.y
            )
            was_point = Point(
                x=1162,
                y=105
            ).to_relative_coordinates_inside_bbox(map_bbox)
            goal_line_bottom_was = RelativePointDTO(
                x=was_point.x,
                y=was_point.y
            )
            key_points_mapping[goal_line_bottom] = key_points_mapping.pop(goal_line_bottom_was)

            out_demo = frame.copy()
            map_demo = map_img.copy()
            for n, (map_p_rel, p) in enumerate(key_points_mapping.items()):
                demo_p = Point.from_relative_coordinates(
                    RelativePoint(p.x, p.y),
                    resolution
                )
                map_p = Point.from_relative_coordinates_inside_bbox(
                    RelativePoint(map_p_rel.x, map_p_rel.y),
                    map_bbox
                )

                out_demo = draw_text(out_demo, str(n), (int(demo_p.x), int(demo_p.y - 10)), (255, 192, 255))
                out_demo = demo_p.visualize_point_on_image(out_demo)

                map_demo = draw_text(map_demo, str(n), (int(map_p.x), int(map_p.y - 10)), (255, 192, 255))
                map_demo = map_p.visualize_point_on_image(map_demo)

            # cv2.imshow("Demo field", out_demo)
            # cv2.imshow("Demo map", map_demo)
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()

            # Patch up and display data to simulate user input
            mapper = PlayersMapper(
                RELATIVE_MAP_BBOX,
                key_points_mapping
            )
            # cv2.imshow("Warped image", mapper.warp_image(frame.copy()))
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()

            player_data_extractor = PlayerDataExtractionService(
                team_predictor,
                mapper,
                PlayerTracker(),
                mask,
                # Absolute coordinates required
                BoundingBox(*mask.get_corners_of_mask())
            )

        assert mapper is not None, "Must have mapper, if map data is provided"
        assert player_data_extractor is not None, "Must have player data extractor instance at this point in code"

        fut = await player_service.add_inference_task_to_queue(frame)
        player_instances = (await fut)[0].to('cpu')

        player_data = player_data_extractor.process_frame(frame, player_instances)

        frame_copy = frame.copy()
        converted_player_data: list[PlayerDataDTO] = []
        for player in player_data:
            # TODO: Replace with actual visualiser wrapper
            player_data_repr = f"{player.tracking_id}: {player.class_id.name[:1]}"

            if player.team_id is not None:
                player_data_repr += f" {player.team_id.name[0]}"

            player_info: PlayerDataDTO = PlayerDataDTO(
                tracking_id=player.tracking_id,
                player_id=None,
                player_name=None,
                team_id=player.team_id,
                class_id=player.class_id,
                player_on_camera=BoxDTO(
                    top_point=RelativePointDTO(
                        x=player.bounding_box_on_camera.min_point.x,
                        y=player.bounding_box_on_camera.min_point.y
                    ),
                    bottom_point=RelativePointDTO(
                        x=player.bounding_box_on_camera.max_point.x,
                        y=player.bounding_box_on_camera.max_point.y
                    )
                ),
                player_on_minimap=RelativePointDTO(
                    x=player.position.x,
                    y=player.position.y
                )
            )

            bbox_real = BoundingBox.from_relative_bounding_box(player.bounding_box_on_camera, resolution)
            frame_copy = bbox_real.visualize_bounding_box(frame_copy)
            draw_text(
                frame_copy,
                player_data_repr,
                (int(bbox_real.min_point.x), int(bbox_real.min_point.y - 10)),
                (22, 99, 33)
            )

            converted_player_data.append(player_info)

        await data_renderer.asend(converted_player_data)

        # cv2.imshow("Field", frame_copy)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        out_video.write(frame_copy)

        frame_n += 1
        print(f"Frame {frame_n:<3} done")

    try:
        await data_renderer.asend(None)

    except StopAsyncIteration:
        pass

    await renderer_task


if __name__ == "__main__":
    start = time.time()
    asyncio.run(main(source_video))
    print(f"Took {round(time.time() - start, 3)}s to render")
