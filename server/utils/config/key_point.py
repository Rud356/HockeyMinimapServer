from pydantic import BaseModel, ConfigDict


class KeyPoint(BaseModel):
    """
    Описывает ключевую точку на мини-карте.

    :param x: Координата X.
    :param y: Координата Y.
    """
    x: int
    y: int

    model_config = ConfigDict(frozen=True)
