from sqlalchemy import Insert
from sqlalchemy.exc import IntegrityError, ProgrammingError

from server.data_storage.exceptions import DataIntegrityError
from server.data_storage.protocols import FramesRepo
from server.data_storage.sql_implementation.tables import Frame
from server.data_storage.sql_implementation.transaction_manager_sqla import TransactionManagerSQLA


class FramesRepoSQLA(FramesRepo):
    def __init__(self, transaction: TransactionManagerSQLA):
        self.transaction: TransactionManagerSQLA = transaction

    async def create_frames(self, video_id: int, frames_count: int) -> int:
        if frames_count < 1 or frames_count > 500_000:
            raise ValueError("Unexpected frames count, must be at least 1 and less than 500000")

        try:
            async with await self.transaction.start_nested_transaction() as tr:
                results = await tr.session.execute(
                    Insert(Frame).returning(Frame.frame_id), [
                        dict(frame_id=frame_n, video_id=video_id) for frame_n in range(frames_count)
                    ]
                )
                await tr.commit()

        except (IntegrityError, ProgrammingError) as err:
            raise DataIntegrityError("Frames duplicate or video not found") from err

        return len(results.all())
