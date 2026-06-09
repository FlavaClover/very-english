import asyncio
import logging
import time
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

DOG_IMAGE_API = "https://dog.ceo/api/breeds/image/random"
DOG_CEO_RATE_LIMIT_MAX = 3
DOG_CEO_RATE_LIMIT_WINDOW_SECONDS = 5
MEDIA_DOWNLOAD_RETRIES = 3
SAMPLE_VIDEO_URLS = (
    "https://www.w3schools.com/html/mov_bbb.mp4",
    "https://download.samplelib.com/mp4/sample-5s.mp4",
    "https://www.learningcontainer.com/wp-content/uploads/2020/05/sample-mp4-file.mp4",
)


class DogCeoRateLimiter:
    """Ограничивает число HTTP-запросов к dog.ceo за скользящее окно."""

    def __init__(
        self,
        max_requests: int = DOG_CEO_RATE_LIMIT_MAX,
        window_seconds: float = DOG_CEO_RATE_LIMIT_WINDOW_SECONDS,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._request_times: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Ждёт слот и регистрирует обращение к dog.ceo.

        :return: None.
        """
        async with self._lock:
            while True:
                now = time.monotonic()
                cutoff = now - self._window_seconds
                self._request_times = [
                    request_time
                    for request_time in self._request_times
                    if request_time > cutoff
                ]
                if len(self._request_times) < self._max_requests:
                    self._request_times.append(now)
                    return
                wait_seconds = self._request_times[0] + self._window_seconds - now
                if wait_seconds > 0:
                    logger.debug(
                        "dog.ceo rate limit: ждём %.1f с (лимит %s/%s с)",
                        wait_seconds,
                        self._max_requests,
                        int(self._window_seconds),
                    )
                    await asyncio.sleep(wait_seconds)


class RemoteMediaFetcher:
    """Скачивает изображения и видео с бесплатных публичных API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        proxy: str | None = None,
        dog_ceo_rate_limiter: DogCeoRateLimiter | None = None,
    ) -> None:
        self._session = session
        self._proxy = proxy
        self._dog_ceo_rate_limiter = dog_ceo_rate_limiter or DogCeoRateLimiter()

    def _request_kwargs(self) -> dict[str, str]:
        if self._proxy:
            return {"proxy": self._proxy}
        return {}

    @staticmethod
    def _is_dog_ceo_url(url: str) -> bool:
        return "dog.ceo" in url

    async def _acquire_dog_ceo_slot(self, url: str) -> None:
        if self._is_dog_ceo_url(url):
            await self._dog_ceo_rate_limiter.acquire()

    async def download_dog_image(self, destination: Path) -> None:
        """Сохраняет случайное фото собаки (dog.ceo).

        :param destination: Путь для записи файла.
        :raises aiohttp.ClientError: Ошибка HTTP или сети.
        """
        logger.info("Запрос фото собаки (dog.ceo)")
        await self._acquire_dog_ceo_slot(DOG_IMAGE_API)
        async with self._session.get(
            DOG_IMAGE_API,
            **self._request_kwargs(),
        ) as response:
            response.raise_for_status()
            payload = await response.json()
        image_url = str(payload["message"])
        await self._download_binary(image_url, destination, source="dog.ceo")

    async def download_sample_video(self, destination: Path) -> None:
        """Сохраняет короткий демо-ролик для видеовизитки.

        Перебирает несколько публичных URL (Google CDN часто отдаёт 403).

        :param destination: Путь для записи файла.
        :raises aiohttp.ClientError: Ошибка HTTP или сети, если все источники недоступны.
        """
        logger.info("Запрос демо-видео для визитки")
        last_error: Exception | None = None
        for video_url in SAMPLE_VIDEO_URLS:
            try:
                await self._download_binary(
                    video_url,
                    destination,
                    source=video_url,
                )
                return
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Демо-видео недоступно (%s): %s",
                    video_url,
                    exc,
                )
        if last_error is not None:
            raise last_error

    async def _download_binary(
        self,
        url: str,
        destination: Path,
        source: str,
    ) -> None:
        last_error: Exception | None = None
        for attempt in range(1, MEDIA_DOWNLOAD_RETRIES + 1):
            try:
                await self._acquire_dog_ceo_slot(url)
                async with self._session.get(
                    url,
                    **self._request_kwargs(),
                ) as response:
                    response.raise_for_status()
                    data = await response.read()
                destination.write_bytes(data)
                size_kb = len(data) / 1024
                logger.info(
                    "Скачано [%s]: %.1f KiB -> %s (попытка %s)",
                    source,
                    size_kb,
                    destination.name,
                    attempt,
                )
                return
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Загрузка [%s] не удалась (попытка %s/%s): %s",
                    source,
                    attempt,
                    MEDIA_DOWNLOAD_RETRIES,
                    exc,
                )
                if attempt < MEDIA_DOWNLOAD_RETRIES:
                    await asyncio.sleep(1)
        if last_error is not None:
            raise last_error
