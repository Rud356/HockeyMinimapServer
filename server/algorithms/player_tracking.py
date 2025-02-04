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

# predicted_classes = {
#     1: "Player",
#     2: "Referee",
#     3: "Goalie"
# }
predicted_classes = [
    "Player",
    "Referee",
    "Goalie"
]
print(Path("../../models/PlayersClassification_720_1.pth").resolve())


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

# Additional filtering based on field position

# Finding bottom point of each bounding box
boxes = filtered_instances.pred_boxes.tensor
x_centers = (boxes[:, 0] + boxes[:, 2]) / 2  # Midpoint of x_min and x_max
y_bottoms = boxes[:, 3]  # y_max (bottom coordinate)
centers: list[list[float]] = torch.stack((x_centers, y_bottoms), dim=1).to("cpu").tolist()
classes_pred: list[PlayerClasses] = [
    PlayerClasses(classifier) for classifier in filtered_instances.pred_classes.to("cpu").tolist()
]
keep = [mask[int(y)-1, int(x)-1] > 0 for x, y in centers]
keep_tensor = torch.tensor(keep, dtype=torch.bool)

filtered_on_field = filtered_instances[keep]

out = vis.draw_instance_predictions(filtered_on_field)
out_mat = out.get_image()[:, :, ::-1]
cv2.imwrite("out.png", img=out_mat)

print(centers)

# Find average luminance of center pixels
def get_luminance(image_):
    """Calculate the average luminance of a pixel in BGR space (OpenCV default).

    Args:
        image: NumPy array representing the image.

    Returns:
        The average luminance value as an integer between 0 and 255.
    """
    # Convert to grayscale using OpenCV's definition for luminance
    gray = cv2.cvtColor(image_, cv2.COLOR_BGR2GRAY)
    return int(gray.mean())

x_centers = (boxes[:, 0] + boxes[:, 2]) / 2  # Midpoint of x_min and x_max
y_tops = (boxes[:, 1] + boxes[:, 3]) / 2.1
centers_pixels: list[list[float]] = torch.stack((x_centers, y_tops), dim=1).to("cpu").tolist()

img_copy = image.copy()
for center in centers_pixels:
    x_center, y_center = map(int, center)

    # Calculate the top-left corner of the kernel based on the 20x20 size
    x_start = x_center - 10
    y_start = y_center - 10

    # Ensure ROI does not go out of bounds
    if (x_start < 0 or x_start + 20 > img_copy.shape[1] or
            y_start < 0 or y_start + 20 > img_copy.shape[0]):
        continue

    # Extract the ROI and calculate luminance
    roi = img_copy[y_start:y_start + 20, x_start:x_start + 20]
    avg_luminance = get_luminance(roi)

    # Create a color block filled with the average luminance
    color_block = np.full((20, 20, 3), (avg_luminance, avg_luminance, avg_luminance), dtype=np.uint8)

    # Replace the ROI in the image copy
    img_copy[y_start:y_start + 20, x_start:x_start + 20] = color_block

    # Draw a rectangle around the kernel to highlight its position
    img_copy = cv2.rectangle(
        img_copy, (x_start, y_start),
        (x_start + 20, y_start + 20), (0, 255, 0), 2
    )

    # Add text with luminance value
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(
        img_copy, str(avg_luminance),
        (x_center, y_center - 10), font, 0.5, (120, 255, 120), 2
    )

cv2.imwrite("out_Blurs.png", img=img_copy)

print("Done!")