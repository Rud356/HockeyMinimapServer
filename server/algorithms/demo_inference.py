# DEMO FILE!
import asyncio
import dataclasses
import math
import pprint
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
from detectron2.utils.visualizer import ColorMode, Visualizer

from server.algorithms.data_types.bounding_box import BoundingBox
from server.algorithms.data_types.line import Line
from server.algorithms.data_types.point import Point
from server.algorithms.enums.coordinate_split import HorizontalPosition, VerticalPosition
from server.algorithms.enums.field_classes_enum import FieldClasses
# predicts teams based on reference images
from server.algorithms.field_predictor_service import FieldPredictorService
from server.algorithms.player_predictor_service import PlayerPredictorService
from server.utils.config.minimap_config import KeyPoint, MinimapKeyPointConfig

MINIMAP_KEY_POINTS = MinimapKeyPointConfig(**
    {
        "top_left_field_point": {"x": 16, "y": 88},
        "bottom_right_field_point": {"x": 1247, "y": 704},

        "left_goal_zone": {"x": 116, "y": 396},
        "right_goal_zone": {"x": 1144, "y": 396},

        "center_line_top": {"x": 630, "y": 92},
        "center_line_bottom": {"x": 630, "y": 700},

        "left_blue_line_top": {"x": 423, "y": 92},
        "left_blue_line_bottom": {"x": 423, "y": 700},

        "right_blue_line_top": {"x": 838, "y": 92},
        "right_blue_line_bottom": {"x": 838, "y": 700},

        "left_goal_line_top": {"x": 99, "y": 105},
        "left_goal_line_bottom": {"x": 99, "y": 360},

        "left_goal_line_after_zone_top": {"x": 99, "y": 433},
        "left_goal_line_after_zone_bottom": {"x": 99, "y": 688},

        "right_goal_line_top": {"x": 1162, "y": 105},
        "right_goal_line_bottom": {"x": 1162, "y": 360},

        "right_goal_line_after_zone_top": {"x": 1162, "y": 433},
        "right_goal_line_after_zone_bottom": {"x": 1162, "y": 688},

        "blue_circle_top_left": {"x": 241, "y": 243},
        "blue_circle_top_right": {"x": 1020, "y": 243},
        "blue_circle_bottom_left": {"x": 241, "y": 550},
        "blue_circle_bottom_right": {"x": 1020, "y": 550}
    }
)


@dataclasses.dataclass
class CameraPosition:
    pos_id: int
    x: int
    y: int

# Сектора с 1 до 6 слева-направо сверху-вниз нумеруются относительно мини-карты
CAMERA_POSITION = CameraPosition(2, 631, 68)


def map_key_points_pixels_to_coordinates_on_minimap(
    minmap_points: MINIMAP_KEY_POINTS,
    camera_sector: int,
    points: list[Point]
):
    pass

def match_circle_points(circle_points: list[Point], camera_position: int) -> dict[KeyPoint, Point]:
    assert camera_position in range(1, 7), "Invalid camera position"

    if not len(circle_points):
        raise ValueError("No points found")

    if len(circle_points) > 4:
        raise ValueError("Invalid circle points amount for blue circles")

    # Image space coordinates
    key_points: dict[tuple[HorizontalPosition, VerticalPosition], KeyPoint] = {
        (HorizontalPosition.top, VerticalPosition.left): MINIMAP_KEY_POINTS.blue_circle_top_left,
        (HorizontalPosition.top, VerticalPosition.right): MINIMAP_KEY_POINTS.blue_circle_top_right,
        (HorizontalPosition.bottom, VerticalPosition.left): MINIMAP_KEY_POINTS.blue_circle_bottom_left,
        (HorizontalPosition.bottom, VerticalPosition.right): MINIMAP_KEY_POINTS.blue_circle_bottom_right
    }

    circle_points_count = len(circle_points)
    # Using distances from top left to judge visible points location
    circle_points.sort(key=lambda p: math.sqrt(p.x ** 2 + p.y ** 2))

    distances_corners = [
        (HorizontalPosition.top, VerticalPosition.left),
        (HorizontalPosition.bottom, VerticalPosition.left),
        (HorizontalPosition.top, VerticalPosition.right),
        (HorizontalPosition.bottom, VerticalPosition.right),
    ]
    resulting_points: list[
        tuple[Point, tuple[HorizontalPosition, VerticalPosition]]
    ] = list(zip(circle_points, distances_corners))

    # Camera is on opposite side
    flips: list[
        tuple[Point, tuple[HorizontalPosition, VerticalPosition]]
    ] = []
    if camera_position < 4:
        for point, mapped_to in resulting_points:
            if mapped_to[0] == HorizontalPosition.top:
                flips.append((point, (HorizontalPosition.bottom, mapped_to[1])))

            else:
                flips.append((point, (HorizontalPosition.top, mapped_to[1])))

        resulting_points = flips

    mapped_coordinates: dict[KeyPoint, Point] = {}

    for point, mapped_to_point in resulting_points:
        map_to = key_points[mapped_to_point]
        mapped_coordinates[map_to] = point

    return mapped_coordinates

async def main(video_path: Path):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    field_service = FieldPredictorService(
        Path("models/FieldDetector_new_based_on_old.pth").resolve(),
        device,
        asyncio.Queue()
    )
    player_service = PlayerPredictorService(
        Path("models/PlayersClassification_720_1.pth").resolve(),
        device,
        asyncio.Queue()
    )

    loop = asyncio.get_running_loop()
    loop.create_task(field_service())
    loop.create_task(player_service())

    cap = cv2.VideoCapture(str(video_path))
    frame_n = 0

    field_mask = None
    center_line: Optional[Line] = None
    center_circle_point: Optional[Point] = None
    red_circles_centers: list[Point] = []
    field_data = {
        "src": [],
        "dest": []
    }

    while cap.isOpened():
        ret, frame = cap.read()

        if not ret:
            break

        if frame_n == 0:
            fut_result: asyncio.Future = await field_service.add_inference_task_to_queue(frame)
            result = await fut_result

            if len(result) == 1:
                result = result[0]
            else:
                raise ValueError("Too many results")

            vis = Visualizer(
                cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                metadata={"thing_classes": list(FieldClasses.__members__.keys())},
                scale=1,
                instance_mode=ColorMode.IMAGE
            )
            out = vis.draw_instance_predictions(result.to("cpu")).get_image()[:, :, ::-1]
            cv2.imshow("Field detected", out)
            cv2.waitKey()
            cv2.destroyAllWindows()

            # Detecting key points
            cpu_instances = result.to("cpu")

            # Inference data
            masks = cpu_instances.pred_masks.numpy()
            boxes = cpu_instances.pred_boxes
            boxes_centers: list[list[float]] = boxes.get_centers().tolist()
            classes_predicted: list[FieldClasses] = [
                FieldClasses(classifier) for classifier in cpu_instances.pred_classes.tolist()
            ]

            # Data
            field_masks = []
            center_lines = {
                "polys": [],
                "bboxes": []
            }
            blue_circles_centers = []

            blue_lines = []
            goal_zone_centers = []

            for mask, center, box, classified_as in zip(masks, boxes_centers, boxes, classes_predicted):
                if classified_as == FieldClasses.Field:
                    field_masks.append(mask)

                elif classified_as == FieldClasses.RedCenterLine:
                    center_lines["polys"].append(mask)
                    center_lines["bboxes"].append(box)

                elif classified_as == FieldClasses.BlueCircle:
                    assert len(center) == 2, "Unexpected length for array with center coordinates"
                    blue_circles_centers.append(Point(center[0], center[1]))

                elif classified_as == FieldClasses.RedCircle:
                    assert len(center) == 2, "Unexpected length for array with center coordinates"
                    red_circles_centers.append(
                        Point(center[0], center[1])
                    )

                elif classified_as == FieldClasses.BlueLine:
                    blue_lines.append({"poly": mask, "bbox": box})

                elif classified_as == FieldClasses.GoalZone:
                    goal_zone_centers.append(Point(center[0], center[1]))

            # Field mask generation
            combined_field_mask = (np.sum(masks, axis=0) * 255).astype(np.uint8)
            # Expanding mask on 10 pixels
            kernel = np.ones((21, 21), np.uint8)  # Create a kernel of size 21x21 (10 pixels on each side)
            field_mask = cv2.dilate(combined_field_mask, kernel, iterations=1)

            # Apply processing to center line
            result_center_line = (np.sum(center_lines["polys"], axis=0) * 255).astype(np.uint8)
            combined_center_line_bounding_box: BoundingBox = BoundingBox.calculate_combined_bbox(
                *center_lines["bboxes"]
            )
            center_line = Line.find_lines(
                result_center_line
            ).clip_line_to_bounding_box(combined_center_line_bounding_box)

            out = center_line.visualize_line_on_image(frame)
            cv2.imshow("Field detected with center line", out)
            cv2.waitKey()
            cv2.destroyAllWindows()

            # Apply processing to blue lines

            # TODO: Process being partially visible
            # Set center circle
            if len(blue_circles_centers) == 1:
                center_circle_point = blue_circles_centers[0]
                out = center_circle_point.visualize_point_on_image(out)
                cv2.imshow("Field detected with center line and circle", out)
                cv2.waitKey()
                cv2.destroyAllWindows()

            for p in red_circles_centers:
                out = p.visualize_point_on_image(out)

            pprint.pprint(match_circle_points(red_circles_centers, CAMERA_POSITION.pos_id))
            cv2.imwrite("out_points_coords.png", out)
            cv2.imshow("Field detected with center line and circle", out)
            cv2.waitKey()
            cv2.destroyAllWindows()

        # Inference
        fut_players_result = await player_service.add_inference_task_to_queue(frame)
        result = await fut_players_result

        frame_n += 1

        if frame_n == 1:
            break

if __name__ == "__main__":
    asyncio.run(
        main(
            Path("static/videos/converted_demo.mp4")
        )
    )
