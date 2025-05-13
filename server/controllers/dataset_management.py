from pathlib import Path
from typing import Annotated

from dishka import FromDishka
from fastapi import APIRouter, HTTPException, Query

from server.algorithms.enums import PlayerClasses, Team
from server.algorithms.services.player_predictor_service import PlayerPredictorService
from server.controllers.dto.subset_created_repsonse import SubsetCreatedResponse
from server.controllers.dto.tracking_points_removed import TrackingPointsRemoved
from server.controllers.endpoints_base import APIEndpoint
from server.controllers.exceptions import UnauthorizedResourceAccess
from server.data_storage.dto import DatasetDTO, UserDTO
from server.data_storage.exceptions import DataIntegrityError, NotFoundError
from server.data_storage.protocols import Repository
from server.utils.config import AppConfig
from server.utils.file_lock import FileLock
from server.views.dataset_view import DatasetView
from server.views.exceptions.mask_not_found import MaskNotFoundError


class DatasetEndpoint(APIEndpoint):
    def __init__(self, router: APIRouter):
        super().__init__(router)
        self.router.add_api_route(
            "/video/{video_id}/dataset",
            self.create_dataset_for_video,
            methods=["post"],
            description="Создает новый датасет разделения на команды к видео",
            tags=["teams dataset"],
            responses={
                400: {
                    "description":
                        "Видео не найдено, для которого создается датасет, или уже существует"
                },
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
            }
        )
        self.router.add_api_route(
            "/datasets/{dataset_id}",
            self.get_dataset_by_id,
            methods=["get"],
            description="Получает объект с набором данных о разделении на команды",
            tags=["teams dataset"],
            responses={
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Набор данных не найден"
                },
            }
        )
        self.router.add_api_route(
            "/datasets/{dataset_id}/size",
            self.get_dataset_size_by_id,
            methods=["get"],
            description="Получает объем набора данных по каждой из команд для конкретного датасета",
            tags=["teams dataset"],
            responses={
                404: {
                    "description":
                        "Набор данных не найден"
                },
            }
        )
        self.router.add_api_route(
            "/datasets/{dataset_id}/subsets/",
            self.create_subset_to_dataset,
            methods=["post"],
            description="Создает поднабор с данными о проекте",
            tags=["teams dataset"],
            responses={
                400: {
                    "description":
                        "Невалидный промежуток кадров для получения примера набора данных"
                },
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Набор данных, видео или файл видео не найден"
                },
                409: {
                    "description":
                        "Видео не откорректировано, или не имеет маску, получаемую через запрос "
                        "на выделение ключевых точек поля"
                },
            }
        )
        self.router.add_api_route(
            "/datasets/subsets/{subset_id}/tracking/{tracking_id}",
            self.remove_tracking_data_for_player,
            methods=["delete"],
            description="Удаляет отслеживание игрока, начиная с кадра",
            tags=["teams dataset"],
            responses={
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Набор данных или видео не найден"
                },
            }
        )
        self.router.add_api_route(
            "/datasets/subsets/{subset_id}/tracking/{tracking_id}/player_class",
            self.modify_player_class,
            methods=["post"],
            description="Изменяет класс отслеживания игрока",
            tags=["teams dataset"],
            responses = {
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Набор данных или видео не найден"
                },
            }
        )
        self.router.add_api_route(
            "/datasets/subsets/{subset_id}/tracking/{tracking_id}/player_team",
            self.modify_player_team,
            methods=["post"],
            description="Изменяет класс отслеживания игрока",
            tags=["teams dataset"],
            responses = {
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Набор данных или видео не найден"
                },
            }
        )

    async def create_dataset_for_video(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int
    ) -> DatasetDTO:
        """
        Создает новый набор данных для видео.

        :param repository: Объект доступа к БД.
        :param current_user: Пользователь системы.
        :param video_id: Идентификатор видео, к которому добавляется датасет.
        :return: Созданный датасет.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            return await DatasetView(repository).create_dataset_for_video(video_id)

        except DataIntegrityError:
            raise HTTPException(
                400,
                "Video not found, which is used for dataset or it already exists"
            )

    async def get_dataset_by_id(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        dataset_id: int
    ) -> DatasetDTO:
        """
        Получает данные о датасете.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Пользователь системы.
        :param dataset_id: Идентификатор набора данных.
        :return: Данные датасета.
        """
        try:
            return await repository.dataset_repo.get_team_dataset_by_id(dataset_id)

        except NotFoundError:
            raise HTTPException(
                404, f"Dataset with id {dataset_id} not found"
            )

        except ValueError:
            raise HTTPException(
                500, "Unexpected data type provided"
            )

    async def get_dataset_size_by_id(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        dataset_id: int
    ) -> dict[Team, int]:
        """
        Получает данные о датасете.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Пользователь системы.
        :param dataset_id: Идентификатор набора данных.
        :return: Данные датасета.
        """
        try:
            return await DatasetView(repository).get_teams_dataset_size(dataset_id)

        except NotFoundError:
            raise HTTPException(404, "Dataset not found")

    async def create_subset_to_dataset(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        player_predictor: FromDishka[PlayerPredictorService],
        file_lock: FromDishka[FileLock],
        app_config: FromDishka[AppConfig],
        dataset_id: int,
        from_frame_id: Annotated[int, Query(ge=0)] = 0,
        frames_amount: Annotated[int, Query(ge=1, le=600)] = 300
    ) -> SubsetCreatedResponse:
        """
        Создает поднабор данных в датасете.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь.
        :param player_predictor: Объект сервиса определения игроков на кадре.
        :param file_lock: Блокировщик доступа к файлам.
        :param app_config: Конфигурация приложения.
        :param dataset_id: Идентификатор набора данных.
        :param from_frame_id: С какого кадра начинать выбор данных.
        :param frames_amount: Сколько кадров должно быть в наборе.
        :return: Идентификатор набора данных.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        static_folder: Path = app_config.static_path

        try:
            subset_id: int = await DatasetView(repository).create_subset_to_dataset(
                dataset_id,
                from_frame_id,
                from_frame_id+frames_amount,
                app_config.prefetch_frame_buffer,
                static_folder,
                file_lock,
                player_predictor
            )

            return SubsetCreatedResponse(
                dataset_id=dataset_id, subset_id=subset_id
            )

        except MaskNotFoundError:
            raise HTTPException(
                409, "Mask not found on disk"
            )

        except FileNotFoundError:
            raise HTTPException(
                409, "Converted video not found on disk"
            )

        except DataIntegrityError:
            raise HTTPException(
                500,
                "Duplicate identifiers found but should have not been"
            )

        except ValueError:
            raise HTTPException(
                500, "Invalid identifiers supplied"
            )

        except NotFoundError:
            raise HTTPException(404, "Video or dataset not found in DB")

        except IndexError:
            raise HTTPException(
                400,
                "Frames range is out of bounds or intersects with other datasets"
            )

    async def remove_tracking_data_for_player(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        subset_id: int,
        tracking_id: int,
        from_frame_id: Annotated[int, Query(ge=0)] = 0,
    ) -> TrackingPointsRemoved:
        """
        Удаляет данные об отслеживании игрока начиная с кадра.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь системы.
        :param subset_id: Идентификатор поднабора.
        :param tracking_id: Идентификатор отслеживания.
        :param from_frame_id: С какого кадра производится отслеживание.
        :return: Информация о количестве удаленных точек.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            points_removed: int = await DatasetView(repository).kill_tracking(
                subset_id,
                tracking_id,
                from_frame_id,
            )
            return TrackingPointsRemoved(points_removed=points_removed)

        except NotFoundError:
            raise HTTPException(
                404,
                "Subset not found"
            )

    async def modify_player_class(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        player_class: Annotated[PlayerClasses, Query()],
        subset_id: int,
        tracking_id: int,
    ) -> bool:
        """
        Изменяет класс выделенного игрока.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Пользователь системы.
        :param player_class: Класс игрока.
        :param subset_id: Идентификатор поднабора данных.
        :param tracking_id: Идентификатор отслеживания игрока.
        :return: Изменения применены.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            return await DatasetView(repository).set_player_class(
                subset_id,
                tracking_id,
                player_class,
            )

        except NotFoundError:
            raise HTTPException(
                404,
                "Subset not found"
            )

    async def modify_player_team(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        player_team: Annotated[Team, Query()],
        subset_id: int,
        tracking_id: int,
    ) -> bool:
        """
        Изменяет команду выделенного игрока.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Пользователь системы.
        :param player_team: Команда игрока.
        :param subset_id: Идентификатор поднабора данных.
        :param tracking_id: Идентификатор отслеживания игрока.
        :return: Изменения применены.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            return await DatasetView(repository).set_player_team(
                subset_id,
                tracking_id,
                player_team,
            )

        except NotFoundError:
            raise HTTPException(
                404,
                "Subset not found"
            )
