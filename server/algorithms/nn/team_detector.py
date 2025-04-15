import torch.nn as nn
from torchvision.models import ResNet, ResNet18_Weights, resnet18


class TeamDetectorModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.resnet18 = resnet18(weights=ResNet18_Weights.DEFAULT)

        for param in self.resnet18.parameters():
            param.requires_grad = False

        # Replace the final fully connected layer
        num_ftrs = self.resnet18.fc.in_features
        self.resnet18.fc = nn.Linear(num_ftrs, 2)  # Home team and away team

    def forward(self, x) -> ResNet:
        x = self.resnet18(x)
        return x
