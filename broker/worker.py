import asyncio
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class Worker(ABC):
    def __init__(self, interval_seconds: float) -> None:
        self._interval_seconds = interval_seconds

    @abstractmethod
    async def execute(self) -> None:
        """Выполняет одну итерацию фоновой задачи."""

    async def run(self) -> None:
        """Запускает бесконечный цикл execute → sleep."""
        logger.info(
            "Worker %s started, interval=%ss",
            self.__class__.__name__,
            self._interval_seconds,
        )
        while True:
            try:
                await self.execute()
            except asyncio.CancelledError:
                logger.info("Worker %s cancelled", self.__class__.__name__)
                raise
            except Exception:
                logger.exception(
                    "Worker %s iteration failed",
                    self.__class__.__name__,
                )
            await asyncio.sleep(self._interval_seconds)

    async def run_once(self) -> None:
        """Выполняет одну итерацию и завершает работу."""
        await self.execute()
