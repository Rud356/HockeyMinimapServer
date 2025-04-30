from pydantic import BaseModel, ConfigDict, Field


class KeyPoint(BaseModel):
    """
    Описывает ключевую точку на мини-карте.

    :param x: Координата X.
    :param y: Координата Y.
    """
    x: int = Field(ge=0)
    y: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)
