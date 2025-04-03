import os
from pathlib import Path

import cv2
import torch
import torch.nn as nn
import torchvision.datasets as datasets
from torchvision.models import resnet18

from server.algorithms.enums.team import Team
from server.algorithms.nn.team_detector_predictor import TeamDetectionPredictor
from server.algorithms.nn.team_detector_teacher import TeamDetectorTeacher, team_detector_transform


class TeamDetectorModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.resnet18 = resnet18(pretrained=True)
        # Replace the final fully connected layer
        num_ftrs = self.resnet18.fc.in_features
        self.resnet18.fc = nn.Linear(num_ftrs, 2)  # Home team and away team

    def forward(self, x):
        x = self.resnet18(x)
        return x

classes_names = list(Team.__members__)
test_dir = '../datasets/custom_validation'
data_dir = '../datasets/custom_dataset'

train_dataset = datasets.ImageFolder(os.path.join(data_dir, 'train'), transform=team_detector_transform)
val_dataset = datasets.ImageFolder(os.path.join(data_dir, 'val'), transform=team_detector_transform)
print(Path(os.path.join(data_dir, 'train')).resolve(), Path(os.path.join(data_dir, 'val')).resolve())

device = "cuda" if torch.cuda.is_available() else "cpu"
trainer = TeamDetectorTeacher(train_dataset, val_dataset, 8, TeamDetectorModel())
model = trainer.train_nn()
predictor: TeamDetectionPredictor = TeamDetectionPredictor(model, team_detector_transform, device)

for image_name in os.listdir(test_dir):
    image_path = os.path.join(test_dir, image_name)
    if os.path.isfile(image_path):
        img = cv2.imread(image_path)
        predicted_team = predictor(img)
        print(f'Image {image_name}: The player belongs to {predicted_team.name} team')
