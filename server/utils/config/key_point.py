from typing import ClassVar

from pydantic import ConfigDict, Field

from server.data_storage.dto import PointDTO


class KeyPoint(PointDTO):
    """
    Описывает ключевую точку на мини-карте.

    :param x: Координата X.
    :param y: Координата Y.
    """
    x: int = Field(ge=0)
    y: int = Field(ge=0)

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True
    ) # noqa: overriding defaults to have it hashable
