from pydantic import BaseModel


class KeyPoint(BaseModel):
    """
    Описывает ключевую точку на мини-карте.

    :param x: Координата X.
    :param y: Координата Y.
    """
    x: int
    y: int
