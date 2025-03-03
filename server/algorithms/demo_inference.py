# DEMO FILE!
import asyncio
import dataclasses
import pprint
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
from detectron2.utils.visualizer import ColorMode, Visualizer
from sort.tracker import SortTracker

from server.algorithms.data_types.bounding_box import BoundingBox
from server.algorithms.data_types.line import Line
from server.algorithms.data_types.point import Point
from server.algorithms.enums.coordinate_split import HorizontalPosition, VerticalPosition
from server.algorithms.enums.field_classes_enum import FieldClasses
from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.field_predictor_service import FieldPredictorService
# predicts teams based on reference images
from server.algorithms.nn.team_detector import predictor
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

        "center_circle": {"x": 630, "y": 396},
        "blue_circle_top_left": {"x": 241, "y": 243},
        "blue_circle_top_right": {"x": 1020, "y": 243},
        "blue_circle_bottom_left": {"x": 241, "y": 550},
        "blue_circle_bottom_right": {"x": 1020, "y": 550}
    }
)


@dataclasses.dataclass
class CameraPositionTest:
    pos_id: int
    x: int
    y: int

# Сектора с 1 до 6 слева-направо сверху-вниз нумеруются относительно мини-карты
CAMERA_POSITION = CameraPositionTest(2, 631, 68)


# TODO: WRITE WRAPPER CODE FOR WORKING WITH LINES EASIER
def determine_quadrant(center_point: Point, point: Point) -> tuple[HorizontalPosition, VerticalPosition]:
    horizontal = HorizontalPosition.top if point.y < center_point.y else HorizontalPosition.bottom
    vertical = VerticalPosition.left if point.x < center_point.x else VerticalPosition.right
    return horizontal, vertical


def match_points(
    points: list[Point],
    camera_position: int,
    key_points: dict[tuple[HorizontalPosition, VerticalPosition], KeyPoint],
    mapping_sides: list[tuple[HorizontalPosition, VerticalPosition]],
    center_point: Optional[Point] = None
) -> dict[KeyPoint, Point]:
    """
    Соотносит точки с переданными квадрантами и сопоставленными им ключевыми точками мини-карты.

    :param points: Точки для соотнесения (до четырех штук).
    :param camera_position: Идентификатор положения камеры.
    :param mapping_sides: Стороны расположения точек для соотнесения.
    :param key_points: Словарь соотнесения ключевых точек по квадрантам поля.
    :param center_point: Опциональная ключевая точка для определения стороны.
    :return: Соотнесенные ключевые точки к точкам из видео.
    """
    if not mapping_sides or len(mapping_sides) != 4:
        raise ValueError("Algorithm must have 4 mapping sides")

    if not points:
        raise ValueError("No points found")

    if len(points) > 4:
        raise ValueError(f"Invalid points amount for key points (must be 4 at max, got {len(points)})")

    resulting_points = [
        (point, determine_quadrant(center_point, point)) for point in points
    ]

    # Camera is on opposite side, so we need to preprocess points
    flips: list[
        tuple[Point, tuple[HorizontalPosition, VerticalPosition]]
    ] = []
    if camera_position < 4:
        for point, mapped_to in resulting_points:
            if mapped_to[0] == HorizontalPosition.top:
                flips.append((point, (HorizontalPosition.bottom, mapped_to[1])))

            elif mapped_to[0] == HorizontalPosition.bottom:
                flips.append((point, (HorizontalPosition.top, mapped_to[1])))

        resulting_points = flips

    # Map coordinates to key points
    mapped_coordinates: dict[KeyPoint, Point] = {}
    for point, mapped_to_point in resulting_points:
        map_to = key_points[mapped_to_point]
        mapped_coordinates[map_to] = point

    return mapped_coordinates


def draw_text(img, text, pos, color):
    return cv2.putText(img, text, pos, cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 2, cv2.LINE_AA)

async def main(video_path: Path):
    TRACKER = SortTracker(2)
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
    homography_transform = None
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out_video = cv2.VideoWriter('output.avi', fourcc, 25.0, (1280, 720))
    out_map_video = cv2.VideoWriter('output_map.avi', fourcc, 25.0, (1259, 770))

    while cap.isOpened():
        ret, frame = cap.read()

        if not ret:
            break

        if frame_n == 0:
            cv2.imwrite("test.png", frame)

        frame_copy = frame.copy()
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

            map_img = cv2.imread("map.png")

            # Data
            field_masks = []
            center_lines = {
                "polys": [],
                "bboxes": []
            }
            blue_circles_centers = []

            blue_lines = []
            goal_lines = []
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

                elif classified_as == FieldClasses.GoalLine:
                    goal_lines.append({"poly": mask, "bbox": box})

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
            blue_lines_processed: list[Line] = []

            # TODO: Process being partially visible
            # Set center circle
            if len(blue_circles_centers) == 1:
                center_circle_point = blue_circles_centers[0]
                out = center_circle_point.visualize_point_on_image(out)
                cv2.imshow("Field detected with center line and circle", out)
                cv2.waitKey()
                cv2.destroyAllWindows()

            for blue_line in blue_lines:
                poly = (blue_line["poly"] * 255).astype(np.uint8)
                line = Line.find_lines(poly)

                if line is not None:
                    line = line.clip_line_to_bounding_box(BoundingBox.calculate_combined_bbox(blue_line["bbox"]))
                    blue_lines_processed.append(line)

            for blue_line in blue_lines_processed:
                out = blue_line.visualize_line_on_image(frame, color=(180, 50, 50))

            cv2.imshow("Field detected with center line and blue lines", out)
            cv2.waitKey()
            cv2.destroyAllWindows()

            # Match points of lines to key points
            key_points_of_lines_sides = [
                (HorizontalPosition.top, VerticalPosition.left),
                (HorizontalPosition.bottom, VerticalPosition.left),
                (HorizontalPosition.top, VerticalPosition.right),
                (HorizontalPosition.bottom, VerticalPosition.right)
            ]
            key_points_of_lines = {
                (HorizontalPosition.top, VerticalPosition.left): MINIMAP_KEY_POINTS.left_blue_line_top,
                (HorizontalPosition.top, VerticalPosition.right): MINIMAP_KEY_POINTS.right_blue_line_top,
                (HorizontalPosition.bottom, VerticalPosition.left): MINIMAP_KEY_POINTS.right_blue_line_bottom,
                (HorizontalPosition.bottom, VerticalPosition.right): MINIMAP_KEY_POINTS.left_blue_line_bottom
            }

            points_by_smallest_distance = [line.min_point for line in blue_lines_processed]
            matched_blue_lines_points = match_points(
                points_by_smallest_distance,
                CAMERA_POSITION.pos_id,
                key_points_of_lines,
                key_points_of_lines_sides,
                center_circle_point
            )
            print("Blue lines mapping:")
            pprint.pprint(matched_blue_lines_points)

            for p in matched_blue_lines_points.values():
                out = p.visualize_point_on_image(out, color=(0, 128, 255))


            # TODO: Generalize by finding first not none point out of some central points in order of: center line top, center circle point, goal zone
            # Processing goal lines
            key_points_of_lines = {
                (HorizontalPosition.top, VerticalPosition.left): MINIMAP_KEY_POINTS.left_goal_line_top,
                (HorizontalPosition.top, VerticalPosition.right): MINIMAP_KEY_POINTS.left_goal_line_after_zone_top,
                (HorizontalPosition.bottom, VerticalPosition.left): MINIMAP_KEY_POINTS.right_goal_line_top,
                (HorizontalPosition.bottom, VerticalPosition.right): MINIMAP_KEY_POINTS.right_goal_line_after_zone_top
            }

            # Apply processing to goal lines
            goal_lines_processed: list[Line] = []

            for goal_line in goal_lines:
                poly = (goal_line["poly"] * 255).astype(np.uint8)
                line = Line.find_lines(poly)

                if line is not None:
                    line = line.clip_line_to_bounding_box(BoundingBox.calculate_combined_bbox(goal_line["bbox"]))
                    goal_lines_processed.append(line)

            for goal_line in goal_lines_processed:
                out = goal_line.visualize_line_on_image(frame, color=(120, 80, 50))

            # TODO: THIS DOES NOT ORDER LINES PROPERLY WHEN MIRRORED, need two pass ordering (first - lines order, second - flips relative to camera)
            # matched_points_goal_lines = match_points(
            #     goal_lines_processed,
            #     CAMERA_POSITION.pos_id,
            #     key_points_of_lines,
            #     key_points_of_lines_sides,
            #     center_line.min_point
            # )

            matched_point_goal_lines = {
                MINIMAP_KEY_POINTS.right_goal_line_after_zone_top: goal_lines_processed[0].min_point,
                MINIMAP_KEY_POINTS.right_goal_line_after_zone_bottom: goal_lines_processed[0].max_point,
            }

            # Process red circles
            for p in red_circles_centers:
                out = p.visualize_point_on_image(out, color=(0, 255, 255))

            red_circles_sides = [
                (HorizontalPosition.top, VerticalPosition.left),
                (HorizontalPosition.top, VerticalPosition.right),
                (HorizontalPosition.bottom, VerticalPosition.left),
                (HorizontalPosition.bottom, VerticalPosition.right),
            ]
            key_points_of_red_circles = {
                (HorizontalPosition.top, VerticalPosition.left): MINIMAP_KEY_POINTS.red_circle_top_left,
                (HorizontalPosition.top, VerticalPosition.right): MINIMAP_KEY_POINTS.red_circle_top_right,
                (HorizontalPosition.bottom, VerticalPosition.left): MINIMAP_KEY_POINTS.red_circle_bottom_left,
                (HorizontalPosition.bottom, VerticalPosition.right): MINIMAP_KEY_POINTS.red_circle_bottom_right
            }

            matched_blue_circle_points = match_points(
                red_circles_centers,
                CAMERA_POSITION.pos_id,
                key_points_of_red_circles,
                red_circles_sides,
                goal_zone_centers[0]
            )
            print("Blue circles mapping")
            pprint.pprint(matched_blue_circle_points)
            cv2.imwrite("out_points_coords.png", out)
            cv2.imshow("Field detected with center line and circle", out)
            cv2.waitKey()
            cv2.destroyAllWindows()

            print("Combined mapping:")
            # FILTER BECAUSE IN FUTURE NOT ALL POINTS MIGHT BE PRESENT
            combined_points = [
                (MINIMAP_KEY_POINTS.center_line_bottom, center_line.min_point),
                *tuple(matched_blue_lines_points.items()),
                (MINIMAP_KEY_POINTS.center_circle, center_circle_point),
                *tuple(matched_blue_circle_points.items()),
                *tuple(matched_point_goal_lines.items()),
                (MINIMAP_KEY_POINTS.right_goal_zone, Point(*goal_zone_centers[0])),
                (MINIMAP_KEY_POINTS.center_line_top, center_line.max_point),
                (MINIMAP_KEY_POINTS.left_blue_line_top, blue_lines_processed[0].max_point)
            ]
            #
            # combined_points = [
            #     (KeyPoint(x=630, y=700), Point(x=902.1317138671875, y=53.99676513671875)),
            #     (KeyPoint(x=838, y=700), Point(x=734.0, y=35.026885986328125)),
            #     (KeyPoint(x=838, y=92), Point(x=1079.17626953125, y=70.30628967285156)),
            #     (KeyPoint(x=630, y=396), Point(x=984.2107543945312, y=254.60848999023438)),
            #     (KeyPoint(x=1020, y=243), Point(x=200.67494201660156, y=390.2291259765625)),
            #     (KeyPoint(x=1020, y=550), Point(x=379.1551818847656, y=101.2994155883789)),
            #     (KeyPoint(x=1162, y=433), Point(x=148.30401611328125, y=180.19952392578125)),
            #     (KeyPoint(x=1162, y=688), Point(x=284.37225341796875, y=44.409393310546875))
            # ]
            #
            combined_points = [
                (KeyPoint(x=630, y=700), Point(x=902.1317138671875, y=53.99676513671875)),
                (KeyPoint(x=838, y=700), Point(x=734.0, y=35.026885986328125)),
                (KeyPoint(x=423, y=700), Point(x=1079.17626953125, y=70.30628967285156)),
                (KeyPoint(x=630, y=396), Point(x=979, y=242)),
                (KeyPoint(x=1020, y=243), Point(x=203, y=367)),
                (KeyPoint(x=1020, y=550), Point(x=381, y=93)),
                (KeyPoint(x=1162, y=433), Point(x=148.30401611328125, y=180.19952392578125)),
                (KeyPoint(x=1162, y=688), Point(x=284.37225341796875, y=44.409393310546875)),
                (KeyPoint(x=1144, y=396), Point(x=153.77694702148438, y=204.68563842773438)),
                (KeyPoint(x=630, y=92), Point(x=1110.5455322265625, y=667.5072021484375)),
                (KeyPoint(x=838, y=92), Point(x=734.0, y=626.1878662109375)),
            ]

            for n, (map_p, p) in enumerate(combined_points):
                out = draw_text(out, str(n), (int(p.x), int(p.y-10)), (255, 192, 255))
                out = p.visualize_point_on_image(out)
                map_img = draw_text(map_img, str(n), (int(map_p.x), int(map_p.y - 10)), (255, 192, 255))
                map_img = Point(int(map_p.x), int(map_p.y)).visualize_point_on_image(map_img)

            pprint.pprint(
                combined_points
            )

            cv2.imshow("Output", out)
            cv2.imshow("Map", map_img)
            cv2.waitKey()
            cv2.destroyAllWindows()

            reprojThreshold = 4.0
            maxIters = 2000
            confidence = 0.9

            src_points = np.array([[pt.x, pt.y] for kp, pt in combined_points], dtype='float32')
            dst_pts = np.array([[kp.x, kp.y] for kp, pt in combined_points], dtype='float32')
            homography_transform, status = cv2.findHomography(src_points, dst_pts, cv2.RANSAC, reprojThreshold, maxIters=maxIters, confidence=confidence)

            # combined_points = [
            #     (MINIMAP_KEY_POINTS.center_line_bottom, center_line.min_point),
            #     *tuple(matched_blue_lines_points.items()),
            #     (MINIMAP_KEY_POINTS.center_circle, center_circle_point),
            #     *tuple(matched_blue_circle_points.items()),
            #     *tuple(matched_point_goal_lines.items())
            # ]

            a = np.array([[p.x, p.y] for _, p in combined_points], dtype='float32')
            a = np.array([a])  # Ensure the shape is (1, N, 2)
            to_map_coordinates = cv2.perspectiveTransform(a, homography_transform)[0]

            height, width = out.shape[:2]
            warped_image = cv2.warpPerspective(out, homography_transform, (width, height))
            cv2.imshow("Warped", warped_image)
            map_img = cv2.resize(map_img, (1280, 720))
            for n, (x, y) in enumerate(to_map_coordinates):
                map_img = draw_text(map_img, str(n), (int(x), int(y - 10)), (255, 192, 255))
                map_img = cv2.circle(map_img, (int(x), int(y)), radius=5, color=(70, 92, 160), thickness=-1)
                print(x, y)
            cv2.imshow("Transformed", map_img)
            cv2.waitKey()
            cv2.destroyAllWindows()

        frame = frame_copy
        # Inference
        fut_players_result = await player_service.add_inference_task_to_queue(frame)
        result = await fut_players_result

        threshold = 0.5
        instances = result[0].to("cpu")
        high_confidence_idxs = instances.scores > threshold
        filtered_instances = instances[high_confidence_idxs].to("cpu")

        # Finding bottom point of each bounding box
        boxes = filtered_instances.pred_boxes.tensor
        x_centers = (boxes[:, 0] + boxes[:, 2]) / 2  # Midpoint of x_min and x_max
        y_bottoms = boxes[:, 3]  # y_max (bottom coordinate)
        centers_bottoms: list[list[float]] = torch.stack((x_centers, y_bottoms), dim=1).to("cpu").tolist()

        keep = [field_mask[int(y) - 1, int(x) - 1] > 0 for x, y in centers_bottoms]
        keep_tensor = torch.tensor(keep, dtype=torch.bool)
        filtered_on_field = filtered_instances[keep_tensor]

        # Finding bottom point of each bounding box
        boxes = filtered_on_field.pred_boxes.tensor
        scores = filtered_on_field.scores
        classes_pred = filtered_on_field.pred_classes
        dets = np.array([np.array([*box, score, class_pred]) for box, score, class_pred in zip(boxes, scores, classes_pred)])
        targets = TRACKER.update(dets, 0).astype(np.int32).tolist()

        object_ids = [obj[4] for obj in targets]
        bounding_boxes = [obj[:4] for obj in targets]
        class_ids = [obj[5] for obj in targets]
        scores = [obj[6] for obj in targets]
        print(targets)

        bboxes = [BoundingBox.calculate_combined_bbox(box) for box in bounding_boxes]
        bounding_boxes_np = np.array(bounding_boxes)
        x_centers = (bounding_boxes_np[:, 0] + bounding_boxes_np[:, 2]) / 2  # Midpoint of x_min and x_max
        y_bottoms = bounding_boxes_np[:, 3]  # y_max (bottom coordinate)
        centers_bottoms: list[list[float]] = np.stack((x_centers, y_bottoms), axis=1).tolist()
        classes_pred: list[PlayerClasses] = [
            PlayerClasses(classifier) for classifier in class_ids
        ]

        center_bottom_points: list[Point] = [Point(*center) for center in centers_bottoms]
        center_points_on_map = np.array([[p.x, p.y] for p in center_bottom_points], dtype='float32')
        center_points_on_map = np.array([center_points_on_map])  # Ensure the shape is (1, N, 2)
        to_map_coordinates = cv2.perspectiveTransform(center_points_on_map, homography_transform)[0]

        player_indexes = [
            n for n, selection_class in enumerate(classes_pred) if selection_class != PlayerClasses.Referee
        ]
        teams = [
            (
                player_index, predictor(
                    bboxes[player_index].cut_out_image_part(frame)
                )
            ) for player_index in player_indexes
        ]
        print(teams)
        map_img = cv2.imread("map.png")

        # Visualize on video and map
        for n, (player_class, bbox, map_coordinates, ids) in enumerate(zip(classes_pred, bboxes, to_map_coordinates, object_ids)):
            text = f"{ids}: {player_class.name}"

            for i, team in teams:
                if i == n:
                    text += f" {team.name}"
                    break

            point_on_map = Point(*map_coordinates)
            out_map = point_on_map.visualize_point_on_image(map_img)
            draw_text(out_map, text, (int(point_on_map.x), int(point_on_map.y-10)), (22, 99, 33))

            out = bbox.visualize_bounding_box(frame)
            draw_text(out, text, (int(bbox.min_point.x), int(bbox.min_point.y-10)), (90, 170, 80))

        try:
            out_video.write(out)
            out_map_video.write(out_map)
            print(f"Frame id: {frame_n}")
            # vis = Visualizer(
            #     frame[:, :, ::-1],
            #     metadata={
            #         "thing_classes": [
            #             "Player",
            #             "Referee",
            #             "Goalie"
            #         ]
            #     },
            #     scale=1,
            #     instance_mode=ColorMode.IMAGE
            # )
            # out = vis.draw_instance_predictions(filtered_on_field)
            # out_mat = out.get_image()[:, :, ::-1]
            # cv2.imshow("Detectron2 out", out_mat)
            # cv2.waitKey()
            # cv2.destroyAllWindows()

        except:
            pass

        frame_n += 1

if __name__ == "__main__":
    asyncio.run(
        main(
            Path("static/videos/converted_demo.mp4")
        )
    )
