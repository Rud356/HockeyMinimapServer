import asyncio

import pytest

from server.algorithms.data_types.disk_usage import DiskUsage
from server.algorithms.disk_space_allocator import (
    DiskSpaceAllocator,
)
from server.algorithms.exceptions.invalid_allocation_overproposition_factor import \
    InvalidAllocationOverPropositionFactor
from server.algorithms.exceptions.invalid_allocation_size import InvalidAllocationSize
from server.algorithms.exceptions.out_of_disk_space import OutOfDiskSpace


@pytest.fixture()
def test_disk_allocator() -> DiskSpaceAllocator:
    return DiskSpaceAllocator()


def get_allocation_chunk_size_to_full(chunks: int, disk_usage: DiskUsage) -> int:
    return round(disk_usage.free / chunks)

async def allocate(test_disk_allocator: DiskSpaceAllocator, size: int, delay: float = 0.05):
    async with test_disk_allocator.preallocate_disk_space(size) as data:
        await asyncio.sleep(delay)
        return data

@pytest.mark.asyncio
async def test_single_allocation(test_disk_allocator: DiskSpaceAllocator):
    # Allocating 10 bytes
    async with test_disk_allocator.preallocate_disk_space(10, 1) as data:
        assert data == 10, "Invalid allocation happened"


@pytest.mark.asyncio
async def test_invalid_allocation(test_disk_allocator: DiskSpaceAllocator):
    with pytest.raises(InvalidAllocationSize):
        async with test_disk_allocator.preallocate_disk_space(-1, 1) as data:
            ...


@pytest.mark.asyncio
async def test_too_small_over_proposition_factor(test_disk_allocator: DiskSpaceAllocator):
    # Allocating 10 bytes
    with pytest.raises(InvalidAllocationOverPropositionFactor):
        async with test_disk_allocator.preallocate_disk_space(10, 0.1) as data:
            ...


@pytest.mark.asyncio
async def test_too_big_over_proposition_factor(test_disk_allocator: DiskSpaceAllocator):
    # Allocating 10 bytes
    with pytest.raises(InvalidAllocationOverPropositionFactor):
        async with test_disk_allocator.preallocate_disk_space(10, 9999) as data:
            ...


@pytest.mark.asyncio
async def test_allocating_chunks_concurrently(test_disk_allocator: DiskSpaceAllocator):
    chunk_size: int = get_allocation_chunk_size_to_full(4, test_disk_allocator.get_disk_usage())
    # Allocating 3 of 4 chunks to have free space for sure
    await asyncio.gather(
        asyncio.create_task(allocate(test_disk_allocator, chunk_size)),
        asyncio.create_task(allocate(test_disk_allocator, chunk_size)),
        asyncio.create_task(allocate(test_disk_allocator, chunk_size))
    )

@pytest.mark.asyncio
async def test_allocating_too_much_space_concurrently(test_disk_allocator: DiskSpaceAllocator):
    chunk_size: int = get_allocation_chunk_size_to_full(4, test_disk_allocator.get_disk_usage())
    # Allocating r of 4 chunks with over proposition will raise error
    try:
        async with asyncio.TaskGroup() as tg:
            # Make other tasks take longer to make sure they are still using memory
            tg.create_task(allocate(test_disk_allocator, chunk_size, 0.1))
            tg.create_task(allocate(test_disk_allocator, chunk_size, 0.1))
            tg.create_task(allocate(test_disk_allocator, chunk_size, 0.1))
            tg.create_task(allocate(test_disk_allocator, chunk_size))

    except ExceptionGroup as exception_group:
        assert isinstance(exception_group.exceptions[0],  OutOfDiskSpace), "Unexpected exception"
