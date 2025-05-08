from server.data_storage.dto import DatasetDTO
from server.data_storage.protocols import Repository


class DatasetView:
    """
    Предоставляет интерфейс работы наборами данных разделения на команды.
    """

    def __init__(self, repository: Repository):
        self.repository: Repository = repository

    async def create_dataset_for_video(self, video_id: int) -> DatasetDTO:
        """
        Создает набор данных разделения на команды для видео.

        :param video_id: Идентификатор видео.
        :return: Представление набора данных.
        :raise DataIntegrityError: Если данные нарушают целостность БД.
        """
        async with self.repository.transaction as tr:
            dataset: DatasetDTO = await self.repository.dataset_repo.create_dataset_for_video(
                video_id
            )
            await tr.commit()

        return dataset

    async def get_team_dataset_by_id(self, dataset_id: int) -> DatasetDTO:
        """
        Получает набор данных разделения команд по идентификатору.

        :param dataset_id: Идентификатор набора данных.
        :return: Набор данных.
        :raise ValueError: Неправильный входной идентификатор.
        :raise NotFoundError: Набор данных не существует.
        """
        return await self.repository.dataset_repo.get_team_dataset_by_id(dataset_id)
