import warnings
from pathlib import Path

from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor

from detectron2.config import get_cfg


with warnings.catch_warnings() as w:
    model_zoo_path = "COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file(model_zoo_path))
    cfg.MODEL.WEIGHTS = str(Path("../../models/PlayersClassification.pth").resolve())
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 3
    cfg.MODEL.DEVICE = "cpu"
    predictor = DefaultPredictor(cfg)

print(Path("../../models/PlayersClassification.pth").resolve())


class PlayerTracker:
    ...
