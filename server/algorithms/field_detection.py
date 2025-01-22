import warnings
import cv2
import torch
from pathlib import Path

from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.utils.visualizer import ColorMode, Visualizer

from detectron2.config import get_cfg

with warnings.catch_warnings() as w:
    model_zoo_path = "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file(model_zoo_path))
    cfg.MODEL.WEIGHTS = str(Path("../../models/FieldDetector.pth").resolve())
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 8
    cfg.MODEL.DEVICE = "cpu"
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

image = cv2.imread(str(Path(r"C:\Users\Rud356-pc\Documents\Projects source code\HockeyMinimapServer\projects\704_c.png")))
image = cv2.resize(image, (1280, 720))

# Set the threshold
threshold = 0.5
class_names = [
    "RedCenterLine", "BlueLine", "RedCircle", "GoalLine",
    "Field", "GoalZone", "Goal", "BlueCircle"
]
vis = Visualizer(
    image[:, :, ::-1],
    metadata={"thing_classes": class_names},
    scale=2,
    instance_mode=ColorMode.IMAGE
)
outputs = predictor(image)

instances = outputs["instances"]
high_confidence_idxs = instances.scores > threshold
filtered_instances = instances[high_confidence_idxs]

out = vis.draw_instance_predictions(filtered_instances.to("cpu"))
out_mat = out.get_image()[:, :, ::-1]
cv2.imwrite("outField.png", img=out_mat)