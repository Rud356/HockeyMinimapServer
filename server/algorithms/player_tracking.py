import warnings
from pathlib import Path

import cv2
import torch
import numpy as np
from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor
from detectron2.utils.visualizer import ColorMode, Visualizer

from server.algorithms.enums.player_classes_enum import PlayerClasses

with warnings.catch_warnings() as w:
    model_zoo_path = "COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file(model_zoo_path))
    cfg.MODEL.WEIGHTS = str(Path("../../models/PlayersClassification_720_1.pth").resolve())
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 3
    cfg.MODEL.DEVICE = "cpu"
    predictor = DefaultPredictor(cfg)


predicted_classes = [
    "Player",
    "Referee",
    "Goalie"
]


class PlayerTracker:
    ...

mask = cv2.imread(str(Path(r"mask.png")), 0)
image = cv2.imread(str(Path(r"../../projects/341.jpeg")))

# image = cv2.resize(image, (700, 700))
vis = Visualizer(
    image[:, :, ::-1],
    metadata={"thing_classes": predicted_classes},
    scale=1,
    instance_mode=ColorMode.IMAGE
)
# Set the threshold
threshold = 0.5

outputs = predictor(image)
print(outputs)

instances = outputs["instances"]
high_confidence_idxs = instances.scores > threshold
filtered_instances = instances[high_confidence_idxs]

# Finding bottom point of each bounding box
boxes = filtered_instances.pred_boxes.tensor
x_centers = (boxes[:, 0] + boxes[:, 2]) / 2  # Midpoint of x_min and x_max
y_bottoms = boxes[:, 3]  # y_max (bottom coordinate)
centers_bottoms: list[list[float]] = torch.stack((x_centers, y_bottoms), dim=1).to("cpu").tolist()
classes_pred: list[PlayerClasses] = [
    PlayerClasses(classifier) for classifier in filtered_instances.pred_classes.to("cpu").tolist()
]


# Additional filtering based on field position
keep = [mask[int(y)-1, int(x)-1] > 0 for x, y in centers_bottoms]
keep_tensor = torch.tensor(keep, dtype=torch.bool)

filtered_on_field = filtered_instances[keep]

out = vis.draw_instance_predictions(filtered_on_field)
out_mat = out.get_image()[:, :, ::-1]
cv2.imwrite("../../projects/out_test.png", img=out_mat)

print(centers_bottoms)

# Find average luminance of center pixels
def get_luminance(image_):
    """Calculate the average luminance of a pixel in BGR space (OpenCV default).

    Args:
        image: NumPy array representing the image.

    Returns:
        The average luminance value as an integer between 0 and 255.
    """
    # Convert to grayscale using OpenCV's definition for luminance
    return cv2.mean(image_)[:3]

team1_color = (180, 180, 180)  # Example color for team 1
team2_color = (64, 64, 64)  # Example color for team 2

def classify_team(avg_color):
    # Simple distance-based classification
    dist_team1 = np.linalg.norm(np.array(avg_color) - np.array(team1_color))
    dist_team2 = np.linalg.norm(np.array(avg_color) - np.array(team2_color))
    team = 'Team 1' if dist_team1 < dist_team2 else 'Team 2'
    return team

centers_pixels: list[list[float]] = filtered_on_field.pred_boxes.get_centers().tolist()

img_copy = image.copy()
field_color = np.array([255, 255, 255], dtype=np.float32)


def find_players_average_colors(image, center_pixels, kernel_size):
    img_copy = image.copy()
    half_kernel = kernel_size // 2
    colors = []

    for center in center_pixels:
        x_center, y_center = map(int, center)

        # Calculate the top-left corner of the kernel based on the kernel size
        x_start = x_center - half_kernel
        y_start = y_center - half_kernel

        # Ensure ROI does not go out of bounds
        if (x_start < 0 or x_start + kernel_size > img_copy.shape[1] or
                y_start < 0 or y_start + kernel_size > img_copy.shape[0]):
            continue

        # Extract the ROI and calculate luminance
        roi = img_copy[y_start:y_start + kernel_size, x_start:x_start + kernel_size]
        avg_luminance = get_luminance(roi)
        colors.append(avg_luminance)

        color_block = np.full((kernel_size, kernel_size, 3), avg_luminance, dtype=np.uint8)
        img_copy[y_start:y_start + kernel_size, x_start:x_start + kernel_size] = color_block

        img_copy = cv2.rectangle(
            img_copy, (x_start, y_start),
            (x_start + kernel_size, y_start + kernel_size), (0, 255, 0), 2
        )

        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            img_copy, classify_team(avg_luminance),
            (x_center, y_center - half_kernel - 10), font, 0.5, (120, 255, 120), 2
        )

    return img_copy

cv2.imwrite("out_Blurs.png", img=find_players_average_colors(image, centers_pixels, 35))

print("Done!")