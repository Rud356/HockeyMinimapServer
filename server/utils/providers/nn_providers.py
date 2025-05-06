from typing import NewType

from dishka import Provider, Scope, provide

from server.algorithms.services.field_predictor_service import FieldPredictorService
from server.algorithms.services.player_predictor_service import PlayerPredictorService


DeviceID = NewType("DeviceID", str)

class NnProvider(Provider):
    """
    Предоставляет доступ к классам, связанных с запуском работы на нейронных сетях.
    """
    def __init__(
        self,
        device_id: str,
        player_predictor: PlayerPredictorService,
        field_predictor: FieldPredictorService
    ) -> None:
        super().__init__()
        self.device_id: DeviceID =  DeviceID(device_id)
        self.player_predictor: PlayerPredictorService = player_predictor
        self.field_predictor: FieldPredictorService = field_predictor

    @provide(scope=Scope.REQUEST)
    def get_player_predictor(self) -> PlayerPredictorService:
        return self.player_predictor

    @provide(scope=Scope.REQUEST)
    def get_field_predictor(self) -> FieldPredictorService:
        return self.field_predictor

    @provide(scope=Scope.REQUEST)
    def get_device_id(self) -> DeviceID:
        return self.device_id
