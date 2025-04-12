from abc import ABC

from fastapi import APIRouter

from server.data_storage.dto import UserDTO


class APIEndpoint(ABC):
    """
    Описывает базовый класс для конечной точки HTTP API.
    """

    def __init__(self, router: APIRouter):
        self.router: APIRouter = router
