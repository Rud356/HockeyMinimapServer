import asyncio
from collections.abc import AsyncGenerator
from typing import TypeVar

StreamedT = TypeVar("StreamedT")


async def _fetch_data_into_buffer(queue: asyncio.Queue[StreamedT], stream: AsyncGenerator[StreamedT, None]) -> None:
    async for data in stream:
        await queue.put(data)


async def buffered_generator(stream: AsyncGenerator[StreamedT, None], size: int) -> AsyncGenerator[StreamedT, None]:
    buffer: asyncio.Queue[StreamedT] = asyncio.Queue(size)
    buffer_filling_task: asyncio.Task[None] = asyncio.create_task(
        _fetch_data_into_buffer(buffer, stream)
    )

    while (not buffer_filling_task.done()) or (not buffer.empty()):
        yield await buffer.get()
