import asyncio
import cProfile
import io
import os
import pstats
from pathlib import Path
from pstats import SortKey
from typing import Optional

import cv2
import numpy
import torch

from server.algorithms.data_types import BoundingBox, Point
from server.algorithms.data_types.field_extracted_data import FieldExtractedData
from server.algorithms.enums import CameraPosition, Team
from server.algorithms.key_point_placer import KeyPointPlacer
from server.algorithms.nn import TeamDetectionPredictor
from server.algorithms.nn.team_detector import predictor
from server.algorithms.player_tracker import PlayerTracker
from server.algorithms.players_mapper import PlayersMapper
from server.algorithms.services.field_data_extraction_service import FieldDataExtractionService
from server.algorithms.services.field_predictor_service import FieldPredictorService
from server.algorithms.services.player_data_extraction_service import PlayerDataExtractionService
from server.algorithms.services.player_predictor_service import PlayerPredictorService
from server.minimap_server import MINIMAP_KEY_POINTS
from server.utils.config.key_point import KeyPoint

os.environ["OPENCV_VIDEO_ACCELERATION"] = "ANY"
source_video: Path = Path("../static/videos/converted_demo.mp4")


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


    loop = asyncio.get_running_loop()
    loop.create_task(field_service())
    loop.create_task(player_service())

    cap = cv2.VideoCapture(str(video_path), cv2.CAP_FFMPEG)
    frame_n = 0
    map_data: Optional[FieldExtractedData] = None
    mapper: Optional[PlayersMapper] = None
    player_data_extractor: Optional[PlayerDataExtractionService] = None

    # Video ouputs
    map_img = cv2.imread("../map.png")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_video = cv2.VideoWriter('../output.mp4', fourcc, 25.0, (1280, 720))
    out_map_video = cv2.VideoWriter('../output_map.mp4', fourcc, 25.0, (1259, 770))
    tracked_players_teams: dict[int, Team] = {}

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

            cv2.imshow("Demo field", out_demo)
            cv2.imshow("Demo map", map_demo)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

            # Patch up and display data to simulate user input
            mapper = PlayersMapper(
                map_bbox,
                map_data.key_points
            )
            cv2.imshow("Warped image", mapper.warp_image(frame.copy()))
            cv2.waitKey(0)
            cv2.destroyAllWindows()

            player_data_extractor = PlayerDataExtractionService(
                team_predictor,
                mapper,
                PlayerTracker(),
                map_data.map_mask,
                map_data.field_bbox
            )

        assert map_data is not None, "Map data is still empty"
        assert mapper is not None, "Must have mapper, if map data is provided"
        assert player_data_extractor is not None, "Must have player data extractor instance at this point in code"

        fut = await player_service.add_inference_task_to_queue(frame)
        player_instances = (await fut)[0].to('cpu')

        player_data = player_data_extractor.process_frame(frame, player_instances, tracked_players_teams)

        frame_copy = frame.copy()
        map_copy = map_img.copy()
        for player in player_data:
            # TODO: Replace with actual visualiser wrapper
            player_data_repr = f"{player.tracking_id}: {player.class_id.name[:1]}"

            if player.team_id is not None:
                player_data_repr += f" {player.team_id.name[0]}"
                tracked_players_teams[player.tracking_id] = player.team_id

            bbox_real = BoundingBox.from_relative_bounding_box(player.bounding_box_on_camera, (720, 1280))
            minimap_point = Point.from_relative_coordinates(player.position, (770, 1259))

            frame_copy = bbox_real.visualize_bounding_box(frame_copy)
            draw_text(
                frame_copy,
                player_data_repr,
                (int(bbox_real.min_point.x), int(bbox_real.min_point.y - 10)),
                (22, 99, 33)
            )

            map_copy = minimap_point.visualize_point_on_image(map_copy)
            draw_text(
                map_copy,
                player_data_repr,
                (int(minimap_point.x), int(minimap_point.y - 10)),
                (22, 99, 33)
            )

        # cv2.imshow("Map", map_copy)
        # cv2.imshow("Field", frame_copy)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        out_video.write(frame_copy)
        out_map_video.write(map_copy)

        frame_n += 1
        print(f"Frame {frame_n:<3} done")


if __name__ == "__main__":
    pr = cProfile.Profile()
    pr.enable()

    asyncio.run(
        main(
            source_video,
            (Path(__file__).parent.parent / "models/FieldDetector_new_based_on_old.pth").resolve(),
            (Path(__file__).parent.parent / "models/PlayersClassification_720_1.pth").resolve()
        )
    )

    pr.disable()
    s = io.StringIO()
    sortby = SortKey.CUMULATIVE
    ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    ps.print_stats()
    print(s.getvalue())
