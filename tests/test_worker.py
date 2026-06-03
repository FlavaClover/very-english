import asyncio

import pytest

from broker.worker import Worker


class CountingWorker(Worker):
    def __init__(self) -> None:
        super().__init__(interval_seconds=0.01)
        self.count = 0

    async def execute(self) -> None:
        self.count += 1
        if self.count >= 2:
            raise asyncio.CancelledError


@pytest.mark.asyncio
async def test_worker_runs_multiple_iterations():
    worker = CountingWorker()
    with pytest.raises(asyncio.CancelledError):
        await worker.run()
    assert worker.count == 2


@pytest.mark.asyncio
async def test_worker_run_once():
    worker = CountingWorker()
    await worker.run_once()
    assert worker.count == 1
