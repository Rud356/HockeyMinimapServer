from pydantic import BaseModel, Field


class ServerSettings(BaseModel):
    """
    Конфигурация серверной части приложения для вывода в сеть.
    """
    host: str
    port: int = Field(default=17600, ge=1, lt=65536)
    is_local_instance: bool
    allowed_cors_domains: list[str]
