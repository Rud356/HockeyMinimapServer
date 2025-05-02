from __future__ import annotations

from typing import Any, Literal, Mapping, TYPE_CHECKING

import torch
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from torch import nn as nn, optim as optim
from torch.utils.data import DataLoader
from torchvision import transforms as transforms
from torchvision.datasets import ImageFolder, VisionDataset

if TYPE_CHECKING:
    from server.algorithms.nn.team_detector import TeamDetectorModel

team_detector_transform = transforms.Compose(
    [
        transforms.Resize((150, 150)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
    ]
)


class TeamDetectorTeacher:
    """
    Класс, занимающийся обучением нейросети на основе входных данных для подготовки нейросети, разделяющей на команды.
    """
    def __init__(
        self,
        train_dataset: ImageFolder,
        val_dataset: ImageFolder,
        epochs: int,
        model: TeamDetectorModel,
        device: Literal['cpu', 'cuda'] | str = 'cpu'
    ):
        """
        Инициализирует класс для обучения модели.

        :param train_dataset: Набор данных для обучения.
        :param val_dataset: Набор данных для оценки качества.
        :param epochs: Количество итераций.
        :param model: Модель машинного обучения.
        :param device: На каком устройстве выполняется обучение.
        """
        self.train_loader: DataLoader[VisionDataset] = DataLoader(train_dataset, batch_size=128)
        self.val_loader: DataLoader[VisionDataset] = DataLoader(val_dataset, batch_size=128)
        self.epochs: int = epochs
        self.model: TeamDetectorModel = model.to(device)
        self.device: str = device

    def train_nn(self) -> TeamDetectorModel:
        """
        Обучает модель машинного обучения примерами игроков из команд.

        :return: Обученная модель машинного обучения.
        """
        train_losses, val_losses = [], []
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(self.model.parameters(), lr=0.00075)
        best_val_loss: float = float('inf')
        best_model_state: Mapping[str, Any] = self.model.state_dict()

        for epoch in range(self.epochs):
            self.model.train()
            running_loss = 0.0
            for inputs, labels in self.train_loader:
                optimizer.zero_grad()
                outputs = self.model(inputs.to(self.device))
                labels = labels.type(torch.LongTensor).to(self.device)
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
                    outputs = self.model(inputs.to(self.device))
                    labels = labels.type(torch.LongTensor).to(self.device)
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

            if val_loss < best_val_loss:
                best_model_state = self.model.state_dict()

            if __debug__:
                print(
                    f"Epoch [{epoch + 1}/{self.epochs}], "
                    f"Loss: {train_losses[-1]:.4f}, "
                    f"Val Loss: {val_losses[-1]:.4f}, "
                    f"Val Acc: {val_accuracy:.2%}, "
                    f"Val Precision: {val_precision:.4f}, "
                    f"Val Recall: {val_recall:.4f}, "
                    f"Val F1 Score: {val_f1:.4f}"
                )

        self.model.load_state_dict(best_model_state)
        # Manual memory cleanup
        del best_model_state
        return self.model
