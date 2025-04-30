import asyncio
from collections.abc import AsyncGenerator
from typing import TypeVar

StreamedT = TypeVar("StreamedT")


async def _fetch_data_into_buffer(
    queue: asyncio.Queue[StreamedT], stream: AsyncGenerator[StreamedT, None]
) -> None:
    """
    Получает значения из генератора и помещает их в буфер.

    :param queue: Очередь, реализующая буфер.
    :param stream: Асинхронный генератор.
    :return: Ничего.
    """
    async for data in stream:
        await queue.put(data)


async def buffered_generator(
    stream: AsyncGenerator[StreamedT, None], size: int
) -> AsyncGenerator[StreamedT, None]:
    """
    Создает буферизованный итератор из асинхронного генератора.

    :param stream: Исходный генератор.
    :param size: Размер буфера.
    :return: Буферизованный генератор.
    """
    buffer: asyncio.Queue[StreamedT] = asyncio.Queue(size)
    buffer_filling_task: asyncio.Task[None] = asyncio.create_task(
        _fetch_data_into_buffer(buffer, stream)
    )

    while (not buffer_filling_task.done()) or (not buffer.empty()):
        yield await buffer.get()
