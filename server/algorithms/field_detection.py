import warnings
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import torch
from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor
from detectron2.structures import Instances
from detectron2.utils.visualizer import ColorMode, Visualizer

device = "cuda" if torch.cuda.is_available() else "cpu"

from server.algorithms.enums.field_classes_enum import FieldClasses

with warnings.catch_warnings() as w:
    model_zoo_path = "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file(model_zoo_path))
    cfg.MODEL.WEIGHTS = str(Path("../../models/FieldDetector_new_based_on_old.pth").resolve())
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 8
    cfg.MODEL.DEVICE = device
    predictor = DefaultPredictor(cfg)


class FieldDetection:
    ...


classes = [
    {"id":1,"name":"RedCenterLine","supercategory":""},
    {"id":2,"name":"BlueLine","supercategory":""},
    {"id":3,"name":"RedCircle","supercategory":""},
    {"id":4,"name":"GoalLine","supercategory":""},
    {"id":5,"name":"Field","supercategory":""},
    {"id":6,"name":"GoalZone","supercategory":""},
    {"id":7,"name":"Goal","supercategory":""},
    {"id":8,"name":"BlueCircle","supercategory":""}
]

image = cv2.imread(str(Path(r"../../projects/out.png")))
image = cv2.resize(image, (1280, 720))

# Set the threshold
threshold = 0.5
class_names = [
    "RedCenterLine", "BlueLine", "RedCircle", "GoalLine",
    "Field", "GoalZone", "Goal", "BlueCircle"
]
vis = Visualizer(
    image[:, :, ::-1],
    metadata={"thing_classes": list(FieldClasses.__members__.keys())},
    scale=1,
    instance_mode=ColorMode.IMAGE
)
outputs = predictor(image)


instances: Instances = outputs["instances"]
high_confidence_idxs = instances.scores > threshold
filtered_instances = instances[high_confidence_idxs]

# Mask generation and tracking points
mask_arrays = []

# Lines
center_line_polys = []
center_line_boxes = []
blue_line_polys = []
goal_line_polys = []

# Centers of circles
circle_centers = []
blue_circle_center: Optional[tuple[float, float]] = None
red_circles_centers: list[tuple[float, float]] = []


# Generating arrays with data
masks = filtered_instances.pred_masks.to("cpu").numpy()
boxes = filtered_instances.pred_boxes.to("cpu")
boxes_centers: list[list[float]] = boxes.get_centers().to("cpu").tolist()
classes_predicted: list[FieldClasses] = [
    FieldClasses(classifier) for classifier in filtered_instances.pred_classes.to("cpu").tolist()
]

# Iterate to generate data about field
classified_as: FieldClasses

def clip_point_to_bbox(x1, y1, bbox):
    x_min, y_min, x_max, y_max = bbox[0], bbox[1], bbox[2], bbox[3]
    x1 = int(np.clip(x1, x_min, x_max))
    y1 = int(np.clip(y1, y_min, y_max))
    return x1, y1


def calculate_combined_bbox(bboxes):
    x_min = min(bbox[0] for bbox in bboxes)
    y_min = min(bbox[1] for bbox in bboxes)
    x_max = max(bbox[2] for bbox in bboxes)
    y_max = max(bbox[3] for bbox in bboxes)
    return [x_min, y_min, x_max, y_max]

for mask, center, box, classified_as in zip(masks, boxes_centers, boxes, classes_predicted):
    if classified_as == FieldClasses.Field:
        mask_arrays.append(mask)

    elif classified_as == FieldClasses.GoalLine:
        center_line_polys.append(mask)
        center_line_boxes.append(box)

    elif classified_as == FieldClasses.BlueCircle:
        assert len(center) == 2, "Unexpected length for array with center coordinates"
        blue_circle_center = (center[0], center[1])

    elif classified_as == FieldClasses.RedCircle:
        assert len(center) == 2, "Unexpected length for array with center coordinates"
        red_circles_centers.append(
            (center[0], center[1])
        )


result = (np.sum(mask_arrays, axis=0) * 255).astype(np.uint8)

# Expanding mask on 10 pixels
kernel = np.ones((21, 21), np.uint8)  # Create a kernel of size 21x21 (10 pixels on each side)
expanded_mask = cv2.dilate(result, kernel, iterations=1)

cv2.imwrite("mask.png", expanded_mask)

result_center_line = (np.sum(center_line_polys, axis=0) * 255).astype(np.uint8)

# Find lines bounding box
combined_bbox = calculate_combined_bbox([b.tolist() for b in center_line_boxes])
x_min, y_min, x_max, y_max = map(int, combined_bbox)

# Useless for just polygon lines
edge_detected = cv2.Canny(result_center_line, 0, 128)
# edge_detected = result_center_line
cv2.imwrite("center_line_img.png", edge_detected)

if result_center_line.any():
    # Iteratively make threshold to give only 1 line?
    lines = cv2.HoughLines(edge_detected, 1, np.pi / 180, 20, 1, 0)
    print(len(lines))
    cv2.imwrite("center_line.png", result_center_line)

    img = cv2.imread("center_line.png")
    for r, theta in lines[:, 0]:
        a = np.cos(theta)
        b = np.sin(theta)

        x0 = a * r
        y0 = b * r
        pt1 = clip_point_to_bbox(int(x0 + 1000 * (-b)), int(y0 + 1000 * (a)), combined_bbox)
        pt2 = clip_point_to_bbox(int(x0 - 1000 * (-b)), int(y0 - 1000 * (a)), combined_bbox)

        output = cv2.line(img, pt1, pt2, (0, 0, 255), 3, cv2.LINE_AA)
        output = cv2.rectangle(output, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)

        cv2.imwrite(f"out_line.png", img=output)

out = vis.draw_instance_predictions(filtered_instances.to("cpu"))
out_mat = out.get_image()[:, :, ::-1]
cv2.imwrite("outField.png", img=out_mat)