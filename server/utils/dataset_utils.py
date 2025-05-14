import torch
from sklearn.model_selection import StratifiedShuffleSplit
from torch import Tensor
from torch.utils.data import Subset


def split_dataset(dataset, train_ratio=0.67) -> tuple[Subset, Subset]:
    """
    Разделяет набор данных в случайном порядке,
    стараясь сохранить соотношения количества классов в поднаборах.

    :param dataset: Исходный набор данных.
    :param train_ratio: Соотношение обучающей выборки к проверочной.
    :return: Обучающая и проверочная выборка.
    """
    # Get the labels for weighted sampling
    labels = torch.tensor([sample[1] for sample in dataset.samples])

    stratified_split = StratifiedShuffleSplit(
        n_splits=1, test_size=1 - train_ratio, random_state=42
    )
    train_idx, val_idx = next(stratified_split.split(torch.zeros(len(labels)), labels))

    train_dataset = Subset(dataset, train_idx.tolist())
    val_dataset = Subset(dataset, val_idx.tolist())

    return train_dataset, val_dataset


def count_labels_in_subsets(dataset, train_indices, val_indices) -> tuple[Tensor, Tensor]:
    """
    Подсчитывает количество классов в каждом из поднаборов.

    :param dataset: Исходный набор.
    :param train_indices: Индексы обучающей выборки.
    :param val_indices: Индексы проверочной выборки.
    :return: Результаты подсчетов.
    """
    # Get the labels for the dataset
    labels = torch.tensor([sample[1] for sample in dataset.samples])

    # Count labels in each subset
    train_labels = labels[train_indices]
    val_labels = labels[val_indices]

    train_label_counts = torch.bincount(train_labels)
    val_label_counts = torch.bincount(val_labels)

    return train_label_counts, val_label_counts
