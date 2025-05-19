from typing import Annotated

from dishka import FromDishka
from fastapi import APIRouter, HTTPException, Query

from server.algorithms.enums import PlayerClasses, Team
from server.algorithms.services.player_predictor_service import PlayerPredictorService
from server.controllers.dto.change_alias_name_request import ChangeAliasNameRequest
from server.controllers.dto.change_alias_team_request import ChangeAliasTeamRequest
from server.controllers.dto.create_player_alias import CreatePlayerAlias
from server.controllers.dto.frames_count_response import FramesCountResponse
from server.controllers.dto.player_alias_created_response import PlayerAliasCreatedResponse
from server.controllers.endpoints_base import APIEndpoint
from server.controllers.exceptions import UnauthorizedResourceAccess
from server.data_storage.dto import FrameDataDTO, UserDTO
from server.data_storage.dto.player_alias import PlayerAlias
from server.data_storage.exceptions import DataIntegrityError, NotFoundError
from server.data_storage.protocols import Repository
from server.utils.config import AppConfig
from server.utils.file_lock import FileLock
from server.utils.providers import RenderBuffer, RenderWorker
from server.views.exceptions import InvalidProjectState, MaskNotFoundError, NotEnoughPlayersUniformExamples
from server.views.player_data_view import PlayerDataView


class PlayerDataEndpoint(APIEndpoint):
    """

    """
    def __init__(self, router: APIRouter):
        super().__init__(router)
        self.router.add_api_route(
            "/videos/{video_id}/frames_range",
            self.get_frames_range_for_video,
            methods=["get"],
            description="Удаляет отслеживание игрока, начиная с кадра",
            tags=["video"],
            responses={
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Видео не найдено"
                },
            }
        )
        self.router.add_api_route(
            "/videos/{video_id}/tracking",
            self.get_partial_tracking_data,
            methods=["get"],
            description="Получает данные об отслеживания игроков в промежутке кадров",
            tags=["player data"],
            responses={
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Не найдена информация в промежутке, или видео не существует"
                }
            }
        )
        self.router.add_api_route(
            "/videos/{video_id}/tracking/all",
            self.get_all_tracking_data,
            methods=["get"],
            description="Получает все данные об отслеживания игроков",
            tags=["player data"],
            responses={
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
            }
        )
        self.router.add_api_route(
            "/videos/{video_id}/tracking",
            self.generate_tracking_data,
            methods=["put"],
            description="Получает данные об отслеживания игроков",
            tags=["player data"],
            responses={
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Видео не найдено, или файлы не найдены"
                },
                409: {
                    "description":
                        "Не выполнены предварительные шаги перед анализом видео"
                },
                425: {
                    "description": "Видео обрабатывается в данный момент"
                }
            }
        )
        self.router.add_api_route(
            "/videos/{video_id}/tracking/map_video",
            self.generate_map_video,
            methods=["put"],
            description="Генерирует видео мини-карты, "
                        "сохраняя видео в файл по пути /static/videos/<UUID видео>/map_video.mp4",
            tags=["player data"],
            responses={
                401: {
                    "description":
                        "Нет валидного токена авторизации"
                },
                404: {
                    "description":
                        "Видео не найдено, или файлы не найдены"
                },
                409: {
                    "description":
                        "Не выполнены предварительные шаги перед отрисовкой карты"
                },
                425: {
                    "description": "Видео обрабатывается в данный момент"
                }
            }
        )
        self.router.add_api_route(
            "/videos/{video_id}/tracking/{tracking_id}/identity",
            self.set_tracking_identity_to_player_alias,
            methods=["patch"],
            description="Изменяет отслеживание игрока, добавляя пользовательское соотнесение",
            tags=["player data"],
            responses={
                200: {
                    "description": "Возвращает количество измененных точек отслеживаний"
                },
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Видео не найдено или идентификатор игрока"
                },
            }
        )
        self.router.add_api_route(
            "/videos/{video_id}/tracking/{tracking_id}/team",
            self.set_team_to_tracking_id,
            methods=["patch"],
            description="Устанавливает команду отслеживанию игрока",
            tags=["player data"],
            responses={
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Видео не найдено или идентификатор игрока"
                },
            }
        )
        self.router.add_api_route(
            "/videos/{video_id}/tracking/{tracking_id}/class",
            self.set_player_class_to_tracking_id,
            methods=["patch"],
            description="Изменяет отслеживание игрока, устанавливая новый класс",
            tags=["player data"],
            responses={
                200: {
                    "description": "Возвращает количество измененных точек отслеживаний"
                },
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Видео не найдено или идентификатор игрока"
                },
            }
        )
        self.router.add_api_route(
            "/videos/{video_id}/tracking/{tracking_id}",
            self.stop_tracking,
            methods=["delete"],
            description="Удаляет отслеживание игрока, начиная с кадра",
            tags=["player data"],
            responses={
                200: {
                    "description": "Возвращает количество удаленных отслеживаний"
                },
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Видео не найдено"
                },
            }
        )
        self.router.add_api_route(
            "/videos/{video_id}/aliases/",
            self.get_player_aliases_for_video,
            methods=["get"],
            description="Получает соотнесение идентификаторов "
                        "пользовательских соотнесений к данным об идентификаторе",
            tags=["player data"],
            responses={
                200: {
                    "description":
                        "Соотнесение идентификаторов пользовательских идентификаторов к данным об идентификаторах"
                },
                401: {
                    "description":
                        "Нет валидного токена авторизации"
                }
            }
        )
        self.router.add_api_route(
            "/videos/{video_id}/aliases/",
            self.create_user_alias_for_players,
            methods=["post"],
            description="Добавляет новый пользовательский идентификатор для игроков",
            tags=["player data"],
            responses={
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Видео не найдено"
                },
            }
        )
        self.router.add_api_route(
            "/player_aliases/{alias_id}",
            self.delete_user_alias_for_player,
            methods=["delete"],
            description="Удаляет пользовательский идентификатор для игроков",
            tags=["player data"],
            responses={
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Идентификатор пользовательского идентификатора не найден"
                },
            }
        )
        self.router.add_api_route(
            "/player_aliases/{alias_id}/name",
            self.change_user_alias_name_for_player,
            methods=["patch"],
            description="Изменяет пользовательский идентификатор для игроков, задавая новое имя",
            tags=["player data"],
            responses={
                400: {
                    "description": "Данные не верные для установки"
                },
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Идентификатор пользовательского идентификатора не найден"
                },
            }
        )
        self.router.add_api_route(
            "/player_aliases/{alias_id}/team",
            self.change_user_alias_team_for_player,
            methods=["patch"],
            description="Изменяет пользовательский идентификатор для игроков, задавая новую команду",
            tags=["player data"],
            responses={
                400: {
                    "description": "Данные не верные для установки"
                },
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {
                    "description":
                        "Идентификатор пользовательского идентификатора не найден"
                },
            }
        )

    async def stop_tracking(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int,
        tracking_id: int,
        from_frame_id: Annotated[int, Query(ge=0)] = 0,
    ) -> int:
        """
        Прекращает отслеживание игрока в видео начиная с кадра.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь системы.
        :param video_id: Идентификатор видео.
        :param tracking_id: Идентификатор отслеживания.
        :param from_frame_id: С какого кадра прекращается отслеживание.
        :return: Количество удаленных точек
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            return await PlayerDataView(repository).kill_tracking(
                video_id, from_frame_id, tracking_id
            )

        except NotFoundError as err:
            raise HTTPException(404, "Tracking data not found") from err

    async def set_tracking_identity_to_player_alias(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int,
        tracking_id: int,
        player_alias_id: Annotated[int, Query(ge=0)],
    ) -> int:
        """
        Прекращает отслеживание игрока в видео начиная с кадра.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь системы.
        :param video_id: Идентификатор видео.
        :param tracking_id: Идентификатор отслеживания.
        :param player_alias_id: Идентификатор пользовательского идентификатора.
        :return: Количество измененных точек.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            return await PlayerDataView(repository).set_player_identity_to_user_id(
                video_id, tracking_id, player_alias_id
            )

        except NotFoundError as err:
            raise HTTPException(404, "Tracking data not found or video") from err

    async def set_team_to_tracking_id(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int,
        tracking_id: int,
        team: Annotated[Team, Query(ge=0)],
        from_frame_id: Annotated[int, Query(ge=0)] = 0,
    ) -> None:
        """
        Устанавливает команду отслеживанию игрока.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь системы.
        :param video_id: Идентификатор видео.
        :param tracking_id: Идентификатор отслеживания.
        :param team: Задание команды для отслеживания.
        :param from_frame_id: С какого кадра произведение переназначение команды отслеживания.
        :return: Количество измененных точек.
        """

        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            await PlayerDataView(repository).set_team_to_tracking_id(
                video_id, tracking_id, from_frame_id, team
            )

        except NotFoundError as err:
            raise HTTPException(404, "Tracking data not found or video") from err

    async def set_player_class_to_tracking_id(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int,
        tracking_id: int,
        player_class: Annotated[PlayerClasses, Query(ge=0)],
        from_frame_id: Annotated[int, Query(ge=0)] = 0,
    ) -> int:
        """
        Прекращает отслеживание игрока в видео начиная с кадра.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь системы.
        :param video_id: Идентификатор видео.
        :param tracking_id: Идентификатор отслеживания.
        :param from_frame_id: Идентификатор номера кадра, на котором сделали изменение.
        :param player_class: Класс игрока.
        :return: Количество измененных точек.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            return await PlayerDataView(repository).set_player_class_to_tracking_id(
                video_id, from_frame_id, tracking_id, player_class
            )

        except NotFoundError as err:
            raise HTTPException(404, "Tracking data not found or video") from err

    async def create_user_alias_for_players(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int,
        player_alias_data: CreatePlayerAlias
    ) -> PlayerAliasCreatedResponse:
        """
        Создает новое соотнесение для игроков.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Пользователь системы.
        :param video_id: Идентификатор видео.
        :param player_alias_data: Данные о пользовательском идентификаторе.
        :return: Идентификатор пользовательского соотнесения.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            alias_id: int = await PlayerDataView(repository).create_user_alias_for_players(
                video_id, player_alias_data.alias_name, player_alias_data.player_team
            )

        except DataIntegrityError as err:
            raise HTTPException(
                404, "Video linked to player custom id not found"
            ) from err

        return PlayerAliasCreatedResponse(player_alias_id=alias_id)

    async def get_player_aliases_for_video(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int,
    ) -> dict[int, PlayerAlias]:
        """
        Получает соотнесение идентификаторов пользовательских соотнесений к данным об идентификаторе.

        :param repository: Объект доступа к БД.
        :param current_user: Пользователь системы.
        :param video_id: Идентификатор видео.
        :return: Соотнесение идентификаторов пользовательских идентификаторов к данным об идентификаторах.
        """
        return await PlayerDataView(repository).get_user_alias_for_players(
            video_id
        )

    async def delete_user_alias_for_player(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        alias_id: int
    ) -> bool:
        """
        Удаляет кастомный идентификатор игрока.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь системы.
        :param alias_id: Идентификатор пользовательского идентификатора для игроков.
        :return: Удалена ли запись.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            return await PlayerDataView(repository).delete_player_alias(
                alias_id
            )

        except NotFoundError as err:
            raise HTTPException(
                404,
                "Custom alias ID not found"
            ) from err

    async def change_user_alias_name_for_player(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        alias_id: int,
        alias_name: ChangeAliasNameRequest
    ) -> None:
        """
        Изменяет имя кастомного идентификатора игрока.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь системы.
        :param alias_id: Идентификатор пользовательского идентификатора для игроков.
        :param alias_name: Имя соотнесения.
        :return: Ничего.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            await PlayerDataView(repository).rename_player_alias(
                alias_id, alias_name.new_name
            )

        except NotFoundError as err:
            raise HTTPException(
                404,
                "Custom alias ID not found"
            ) from err

        except DataIntegrityError as err:
            raise HTTPException(
                400,
                "Invalid data supplied"
            ) from err

    async def change_user_alias_team_for_player(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        alias_id: int,
        alias_team: ChangeAliasTeamRequest
    ) -> None:
        """
        Изменяет команду кастомного идентификатора игрока.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь системы.
        :param alias_id: Идентификатор пользовательского идентификатора для игроков.
        :param alias_team: Новая команда пользовательского идентификатора.
        :return: Ничего.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            await PlayerDataView(repository).change_player_alias_team(
                alias_id, alias_team.new_team
            )

        except NotFoundError as err:
            raise HTTPException(
                404,
                "Custom alias ID not found"
            ) from err

        except DataIntegrityError as err:
            raise HTTPException(
                400,
                "Invalid data supplied"
            ) from err

    async def get_frames_range_for_video(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int,
    ) -> FramesCountResponse:
        """
        Получает номер первого и последнего кадра видео.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь.
        :param video_id: Идентификатор видео.
        :return: Промежуток кадров.
        """
        try:
            from_frame, to_frame = await PlayerDataView(repository).get_frames_min_and_max_ids_in_video(
                video_id
            )
        except NotFoundError:
            raise HTTPException(404, "Video not found")

        return FramesCountResponse(
            from_frame=from_frame,
            to_frame=to_frame
        )

    async def generate_tracking_data(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int,
        file_lock: FromDishka[FileLock],
        app_config: FromDishka[AppConfig],
        player_predictor: FromDishka[PlayerPredictorService],
    ) -> None:
        """
        Получает информацию об отслеживании игроков.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь.
        :param video_id: Идентификатор видео.
        :param file_lock: Блокировщик доступа к файлам.
        :param app_config: Конфигурация приложения.
        :param player_predictor: Сервис поиска игроков на изображении.
        :return: Ничего.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            await PlayerDataView(repository).generate_tracking_data(
                video_id,
                app_config.prefetch_frame_buffer,
                file_lock,
                app_config.static_path,
                player_predictor
            )

        except MaskNotFoundError:
            raise HTTPException(
                404, "Mask file not found"
            )

        except FileNotFoundError:
            raise HTTPException(
                404, "Video file not found"
            )

        except NotFoundError:
            raise HTTPException(
                404, "Video not found in database"
            )

        except InvalidProjectState:
            raise HTTPException(
                409,
                "Project state conflicts and does not allow to process video"
            )

        except NotEnoughPlayersUniformExamples:
            raise HTTPException(
                409, "More uniform examples required"
            )

        except DataIntegrityError as err:
            raise HTTPException(
                409, "Data is already in database"
            ) from err

        except TimeoutError:
            raise HTTPException(
                425,
                "Currently processing video"
            )

    async def generate_map_video(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        file_lock: FromDishka[FileLock],
        app_config: FromDishka[AppConfig],
        map_buffer: FromDishka[RenderBuffer],
        map_renderer: FromDishka[RenderWorker],
        video_id: int
    ) -> None:
        """
        Генерирует видео в папке загруженного видео, с названием map_video\.mp4.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Текущий пользователь системы.
        :param file_lock: Блокировщик доступа к файлам.
        :param app_config: Конфигурация приложения.
        :param map_buffer: Объем буфера вывода карты.
        :param map_renderer: Исполнитель отрисовки.
        :param video_id: Идентификатор карты.
        :return: Ничего.
        """
        try:
            await PlayerDataView(repository).generate_map_video(
                video_id,
                file_lock,
                app_config.minimap_config,
                map_buffer,
                map_renderer,
                app_config.video_processing,
                app_config.static_path
            )

        except TimeoutError:
            raise HTTPException(
                425, "Currently generating minimap"
            )

        except InvalidProjectState as err:
            raise HTTPException(
                409,
                "Previous steps in processing are not done before this step"
            ) from err

        except FileNotFoundError as err:
            raise HTTPException(
                404, "Video file or map file not found"
            ) from err

    async def get_all_tracking_data(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int
    ) -> FrameDataDTO:
        """
        Получает всю информацию о перемещениях игроков на видео.

        :param repository: Объект доступа к БД.
        :param current_user: Текущий пользователь системы.
        :param video_id: Идентификатор видео.
        :return: Данные о перемещениях в кадре.
        """
        return await PlayerDataView(repository).get_all_tracking_data(video_id)

    async def get_partial_tracking_data(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int,
        from_frame_id: Annotated[int, Query(ge=0)] = 0,
        frames_amount: Annotated[int, Query(ge=1, le=600)] = 300
    ):
        """
        Получает информацию о перемещениях игроков на видео.

        :param repository: Объект доступа к БД.
        :param current_user: Текущий пользователь системы.
        :param video_id: Идентификатор видео.
        :param from_frame_id: С какого кадра начинать выбор данных.
        :param frames_amount: Сколько кадров должно быть выбрано.
        :return: Данные о перемещениях в кадре.
        """
        try:
            return await PlayerDataView(repository).get_tracking_from_frames(
                video_id,
                frames_amount,
                from_frame_id
            )

        except IndexError:
            raise HTTPException(
                404,
                "Videos frames not found"
            )
