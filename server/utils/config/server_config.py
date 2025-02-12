from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    """
    Конфигурация серверной части приложения для вывода в сеть.
    """
    host: str
    port: int = Field(ge=1, lt=65536)
    is_local_instance: bool