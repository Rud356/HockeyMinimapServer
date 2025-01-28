import warnings
from pathlib import Path

import cv2
import torch
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


image = cv2.imread(str(Path(r"../../projects/510.jpeg")))
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
out = vis.draw_instance_predictions(filtered_instances.to("cpu"))
out_mat = out.get_image()[:, :, ::-1]
cv2.imwrite("out.png", img=out_mat)

# Finding bottom point of each bounding box
boxes = filtered_instances.pred_boxes.tensor
x_centers = (boxes[:, 0] + boxes[:, 2]) / 2  # Midpoint of x_min and x_max
y_bottoms = boxes[:, 1]  # y_min
centers: list[list[float]] = torch.stack((x_centers, y_bottoms), dim=1).to("cpu").tolist()
classes_pred: list[PlayerClasses] = [
    PlayerClasses(classifier) for classifier in filtered_instances.pred_classes.to("cpu").tolist()
]
scores: list[float] = filtered_instances.scores.to("cpu").tolist()
print(centers)
print("Done!")