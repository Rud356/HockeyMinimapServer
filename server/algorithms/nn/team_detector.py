import os

import cv2
import torch.nn as nn
import torch.nn.functional as F
import torchvision.datasets as datasets

from server.algorithms.enums.teams import Team
from server.algorithms.nn.team_detector_predictor import TeamDetectionPredictor
from server.algorithms.nn.team_detector_teacher import TeamDetectorTeacher, team_detector_transform


class TeamDetectorModel(nn.Module):
    def __init__(self):
        super(TeamDetectorModel, self).__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2, padding=0)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.fc1 = nn.Linear(128 * 18 * 18, 512)
        self.dropout = nn.Dropout(0.5)
        self.fc2 = nn.Linear(512, 2)  # Home team and away team

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = self.pool(F.relu(self.conv3(x)))
        x = x.view(-1, 128 * 18 * 18)
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x


classes_names = list(Team.__members__)
test_dir = 'datasets/custom_validation'
data_dir = 'datasets/custom_dataset'

train_dataset = datasets.ImageFolder(os.path.join(data_dir, 'train'), transform=team_detector_transform)
val_dataset = datasets.ImageFolder(os.path.join(data_dir, 'val'), transform=team_detector_transform)

trainer = TeamDetectorTeacher(train_dataset, val_dataset, 8, TeamDetectorModel())
model = trainer.train_nn()
predictor = TeamDetectionPredictor(model, team_detector_transform)

for image_name in os.listdir(test_dir):
    image_path = os.path.join(test_dir, image_name)
    if os.path.isfile(image_path):
        img = cv2.imread(image_path)
        predicted_team = predictor(img)
        print(f'Image {image_name}: The player belongs to {predicted_team.name} team')
