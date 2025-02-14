import os
from enum import IntEnum, auto

import cv2
import numpy
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torchvision.datasets as datasets
import torchvision.transforms as transforms
from PIL import Image
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from torch.utils.data import DataLoader
from torchvision.datasets import ImageFolder


class Team(IntEnum):
    Home = auto()
    Away = auto()


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


transform = transforms.Compose(
    [
        transforms.Resize((150, 150)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    ]
)
classes_names = list(Team.__members__)
test_dir = '../../../datasets/custom_validation'
data_dir = '../../../datasets/custom_dataset'

train_dataset = datasets.ImageFolder(os.path.join(data_dir, 'train'), transform=transform)
val_dataset = datasets.ImageFolder(os.path.join(data_dir, 'val'), transform=transform)

class TeamDetectorTeacher:
    def __init__(self, train_dataset: ImageFolder, val_dataset: ImageFolder, epochs: int, model: TeamDetectorModel):
        self.train_loader: DataLoader[ImageFolder] = DataLoader(train_dataset, batch_size=32, shuffle=True)
        self.val_loader: DataLoader[ImageFolder] = DataLoader(val_dataset, batch_size=32, shuffle=False)
        self.epochs: int = epochs
        self.model: TeamDetectorModel = model

    def train_nn(self) -> TeamDetectorModel:
        train_losses, val_losses = [], []
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)

        for epoch in range(self.epochs):
            self.model.train()
            running_loss = 0.0
            for inputs, labels in self.train_loader:
                optimizer.zero_grad()
                outputs = self.model(inputs)
                labels = labels.type(torch.LongTensor)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                running_loss += loss.item()

            train_losses.append(running_loss / len(self.train_loader))

            self.model.eval()
            val_loss = 0.0
            all_labels = []
            all_preds = []
            with torch.no_grad():
                for inputs, labels in self.val_loader:
                    outputs = self.model(inputs)
                    labels = labels.type(torch.LongTensor)
                    loss = criterion(outputs, labels)
                    val_loss += loss.item()
                    _, preds = torch.max(outputs, 1)
                    all_labels.extend(labels.tolist())
                    all_preds.extend(preds.tolist())

            val_losses.append(val_loss / len(self.val_loader))
            val_accuracy = accuracy_score(all_labels, all_preds)
            val_precision = precision_score(all_labels, all_preds, average='macro', zero_division=1)
            val_recall = recall_score(all_labels, all_preds, average='macro', zero_division=1)
            val_f1 = f1_score(all_labels, all_preds, average='macro', zero_division=1)

            print(
                f"Epoch [{epoch + 1}/{self.epochs}], "
                f"Loss: {train_losses[-1]:.4f}, "
                f"Val Loss: {val_losses[-1]:.4f}, "
                f"Val Acc: {val_accuracy:.2%}, "
                f"Val Precision: {val_precision:.4f}, "
                f"Val Recall: {val_recall:.4f}, "
                f"Val F1 Score: {val_f1:.4f}"
            )

        return self.model


class TeamDetectionPredictor:
    def __init__(self, model: TeamDetectorModel, transform_inputs):
        self.model = model
        self.transform = transform_inputs

    def __call__(self, image: numpy.ndarray) -> Team:
        image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        image = transform(image).unsqueeze(0)

        with torch.no_grad():
            output = self.model(image)
            _, predicted = torch.max(output, 1)

            if predicted.item() == Team.Home:
                return Team.Home

            elif predicted.item() == Team.Away:
                return Team.Away

            return Team.Away

trainer = TeamDetectorTeacher(train_dataset, val_dataset, 8, TeamDetectorModel())
model = trainer.train_nn()
predictor = TeamDetectionPredictor(model, transform)

for image_name in os.listdir(test_dir):
    image_path = os.path.join(test_dir, image_name)
    if os.path.isfile(image_path):
        img = cv2.imread(image_path)
        predicted_team = predictor(img)
        print(f'Image {image_name}: The player belongs to {predicted_team.name} team')
