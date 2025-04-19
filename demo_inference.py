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

from server.algorithms.data_types import BoundingBox, CV_Image, Point
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
from server.algorithms.services.player_predictor_service import PlayerPredictorService
from server.data_storage.dto import BoxDTO, PointDTO
from server.data_storage.dto.player_data_dto import PlayerDataDTO
from server.minimap_server import MINIMAP_KEY_POINTS
from server.utils.config import VideoPreprocessingConfig
from server.utils.config.key_point import KeyPoint

os.environ["OPENCV_VIDEO_ACCELERATION"] = "ANY"
source_video: Path = Path("tests/videos/converted_demo.mp4")

classes_names = list(Team.__members__)
test_dir = 'datasets/custom_validation'
data_dir = 'datasets/custom_dataset'

train_dataset = datasets.ImageFolder(os.path.join(data_dir, 'train'), transform=team_detector_transform)
val_dataset = datasets.ImageFolder(os.path.join(data_dir, 'val'), transform=team_detector_transform)
print(Path(os.path.join(data_dir, 'train')).resolve(), Path(os.path.join(data_dir, 'val')).resolve())

device = "cuda" if torch.cuda.is_available() else "cpu"
trainer = TeamDetectorTeacher(train_dataset, val_dataset, 100, TeamDetectorModel())
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


async def main(video_path: Path, field_model: Path, players_model: Path):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    field_service = FieldPredictorService(
        field_model.resolve(),
        device,
        asyncio.Queue()
    )
    player_service = PlayerPredictorService(
        players_model.resolve(),
        device,
        asyncio.Queue()
    )
    # DEMO RESOLUTION, FIGURED OUT IN RUNTIME
    key_point_placer = KeyPointPlacer(MINIMAP_KEY_POINTS, CameraPosition.top_middle_point, (1280, 720))

    team_predictor: TeamDetectionPredictor = predictor

    map_img = cv2.imread("map.png")
    # Video output streams
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_video = cv2.VideoWriter('output.mp4', fourcc, 25.0, (1280, 720))

    video_render_service = MapVideoRendererService(
        ThreadPoolExecutor(1),
        25.0,
        Path('output_map.mp4'),
        map_img,
        video_processing_config=VideoPreprocessingConfig(video_width=1280, video_height=720, crf=30)
    )
    data_renderer: AsyncGenerator[int, list[PlayerDataDTO] | None] = video_render_service.data_renderer()
    await data_renderer.asend(None)

    loop = asyncio.get_running_loop()
    loop.create_task(field_service())
    loop.create_task(player_service())
    renderer_task = loop.create_task(video_render_service.run())

    cap = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)
    frame_n = 0
    map_data: Optional[FieldExtractedData] = None
    mapper: Optional[PlayersMapper] = None
    player_data_extractor: Optional[PlayerDataExtractionService] = None

    map_bbox: Optional[BoundingBox] = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_n == 0:
            map_data = await field_data(frame.copy(), field_service, key_point_placer)

            # Fix point data
            map_data.key_points[KeyPoint(x=423, y=520)] = map_data.key_points.pop(MINIMAP_KEY_POINTS.left_blue_line_bottom)
            map_data.key_points[KeyPoint(x=1162, y=244)] = map_data.key_points.pop(KeyPoint(x=1162, y=105))

            map_bbox = BoundingBox(
                Point(MINIMAP_KEY_POINTS.top_left_field_point.x, MINIMAP_KEY_POINTS.top_left_field_point.y),
                Point(MINIMAP_KEY_POINTS.bottom_right_field_point.x, MINIMAP_KEY_POINTS.bottom_right_field_point.y)
            )

            out_demo = frame.copy()
            map_demo = map_img.copy()
            for n, (map_p, p) in enumerate(map_data.key_points.items()):
                out_demo = draw_text(out_demo, str(n), (int(p.x), int(p.y - 10)), (255, 192, 255))
                out_demo = p.visualize_point_on_image(out_demo)

                map_demo = draw_text(map_demo, str(n), (int(map_p.x), int(map_p.y - 10)), (255, 192, 255))
                map_demo = Point(int(map_p.x), int(map_p.y)).visualize_point_on_image(map_demo)

            # cv2.imshow("Demo field", out_demo)
            # cv2.imshow("Demo map", map_demo)
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()

            # Patch up and display data to simulate user input
            mapper = PlayersMapper(
                map_bbox,
                map_data.key_points
            )
            # cv2.imshow("Warped image", mapper.warp_image(frame.copy()))
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()

            player_data_extractor = PlayerDataExtractionService(
                team_predictor,
                mapper,
                PlayerTracker(),
                map_data.map_mask,
                map_data.field_bbox
            )

        assert map_bbox is not None, "Map bbox must be not None"
        assert map_data is not None, "Map data is still empty"
        assert mapper is not None, "Must have mapper, if map data is provided"
        assert player_data_extractor is not None, "Must have player data extractor instance at this point in code"

        fut = await player_service.add_inference_task_to_queue(frame)
        player_instances = (await fut)[0].to('cpu')

        player_data = player_data_extractor.process_frame(frame, player_instances)

        frame_copy = frame.copy()
        map_copy = map_img.copy()

        converted_player_data: list[PlayerDataDTO] = []
        for player in player_data:
            # TODO: Replace with actual visualiser wrapper
            player_data_repr = f"{player.tracking_id}: {player.class_id.name[:1]}"

            if player.team_id is not None:
                player_data_repr += f" {player.team_id.name[0]}"

            bbox_real = BoundingBox.from_relative_bounding_box(player.bounding_box_on_camera, (720, 1280))
            minimap_point = Point.from_relative_coordinates_inside_bbox(player.position, map_bbox)

            frame_copy = bbox_real.visualize_bounding_box(frame_copy)
            draw_text(
                frame_copy,
                player_data_repr,
                (int(bbox_real.min_point.x), int(bbox_real.min_point.y - 10)),
                (22, 99, 33)
            )

            converted_player_data.append(
                PlayerDataDTO(
                    tracking_id=player.tracking_id,
                    player_id=None,
                    player_name=None,
                    team_id=player.team_id,
                    class_id=player.class_id,
                    player_on_camera=BoxDTO(
                        top_point=PointDTO(
                            x=bbox_real.min_point.x,
                            y=bbox_real.min_point.y
                        ),
                        bottom_point=PointDTO(
                            x=bbox_real.max_point.x,
                            y=bbox_real.max_point.y
                        )
                    ),
                    player_on_minimap=PointDTO(
                        x=minimap_point.x,
                        y=minimap_point.y
                    )
                )
            )

        await data_renderer.asend(converted_player_data)

        # cv2.imshow("Map", map_copy)
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
    asyncio.run(
        main(
            source_video,
            (Path(__file__).parent / "models/FieldDetector_new_based_on_old.pth").resolve(),
            (Path(__file__).parent / "models/PlayersClassification_720_1.pth").resolve()
        )
    )
    print(f"Took {round(time.time() - start, 3)}s to render")
