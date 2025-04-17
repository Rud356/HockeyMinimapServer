from abc import ABC

from fastapi import APIRouter


class APIEndpoint(ABC):
    """
    Описывает базовый класс для конечной точки HTTP API.
    """

    def __init__(self, router: APIRouter):
        self.router: APIRouter = router
