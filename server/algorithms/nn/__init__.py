import torch

from .team_detector import TeamDetectorModel # noqa: used as exports
from .team_detector_teacher import TeamDetectorTeacher, team_detector_transform # noqa: used as exports
from .team_detector_predictor import TeamDetectionPredictor # noqa: used as exports


torch.set_float32_matmul_precision('medium')
device: str = "cuda" if torch.cuda.is_available() else "cpu"


__all__ = (
    "TeamDetectorTeacher",
    "TeamDetectorModel",
    "TeamDetectionPredictor",
    "team_detector_transform",
    "device"
)
