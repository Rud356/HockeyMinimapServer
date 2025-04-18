from typing import Optional, Sequence, cast

from sqlalchemy import Delete, Select
from sqlalchemy.exc import IntegrityError, ProgrammingError

from server.data_storage.dto import MinimapDataDTO, PointDTO
from server.data_storage.exceptions import DataIntegrityError, NotFoundError
from server.data_storage.protocols import MapDataRepo
from server.data_storage.sql_implementation.tables import MapData, Point
from server.data_storage.sql_implementation.transaction_manager_sqla import TransactionManagerSQLA


class MapDataRepoSQLA(MapDataRepo):
    def __init__(self, transaction: TransactionManagerSQLA):
        self.transaction: TransactionManagerSQLA = transaction

    async def create_point_mapping_for_video(
        self, video_id: int, mapping: dict[PointDTO, PointDTO]
    ) -> int:
        try:
            async with await self.transaction.start_nested_transaction() as tr:
                tr.session.add_all(
                    [
                        MapData(
                            video_id=video_id,
                            point_on_camera=Point(x=video_point.x, y=video_point.y),
                            point_on_minimap=Point(x=map_point.x, y=map_point.y),
                        )
                        for map_point, video_point in mapping.items()
                    ]
                )
                await tr.commit()

        except (ProgrammingError, IntegrityError) as err:
            raise DataIntegrityError("Integrity check failed") from err

        return len(mapping)

    async def get_points_mapping_for_video(self, video_id: int) -> list[MinimapDataDTO]:
        result: Sequence[MapData] = (await self.transaction.session.execute(
            Select(MapData).where(MapData.video_id == video_id)
        )).scalars().all()

        return [
            MinimapDataDTO(
                map_data_id=map_data_point.map_data_id,
                point_on_camera=PointDTO(x=map_data_point.point_on_camera.x, y=map_data_point.point_on_camera.y),
                point_on_minimap=PointDTO(x=map_data_point.point_on_minimap.x, y=map_data_point.point_on_minimap.y),
                is_used=map_data_point.is_used
            )
            for map_data_point in result
        ]

    async def drop_all_mapping_points_for_video(self, video_id: int) -> int:
        async with await self.transaction.start_nested_transaction() as tr:
            results: Sequence[MapData] = (await tr.session.scalars(
                Select(MapData).where(MapData.video_id == video_id)
            )).all()

            for to_delete in results:
                await self.transaction.session.delete(to_delete)

            await tr.commit()
            return len(results)

    async def edit_point_from_mapping(
        self,
        map_data_id: int,
        point_on_camera: Optional[PointDTO] = None,
        point_on_minimap: Optional[PointDTO] = None,
        is_used: Optional[bool] = None
    ) -> bool:
        modified: bool = False

        try:
            async with await self.transaction.start_nested_transaction() as tr:
                data_point: Optional[MapData] = (await self.transaction.session.execute(
                    Select(MapData).where(MapData.map_data_id == map_data_id)
                )).scalar_one_or_none()

                if data_point is None:
                    raise NotFoundError("Data point with specified ID wasn't found")

                if point_on_camera is not None:
                    data_point.point_on_camera.x = point_on_camera.x
                    data_point.point_on_camera.y = point_on_camera.y
                    modified = True

                if point_on_minimap is not None:
                    data_point.point_on_minimap.x = point_on_minimap.x
                    data_point.point_on_minimap.y = point_on_minimap.y
                    modified = True

                if is_used is not None:
                    data_point.is_used = is_used
                    modified = True

                await tr.commit()

        except (IntegrityError, ProgrammingError) as err:
            raise DataIntegrityError("Constraints are broken when updating map data point") from err

        return modified
