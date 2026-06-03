import asyncio
import logging
from pathlib import Path

import aiohttp

logger = logging.getLogger(__name__)

DOG_IMAGE_API = "https://dog.ceo/api/breeds/image/random"
CAT_IMAGE_API = "https://api.thecatapi.com/v1/images/search?limit=1&mime_types=jpg"
MEDIA_DOWNLOAD_RETRIES = 3
SAMPLE_VIDEO_URLS = (
    "https://www.w3schools.com/html/mov_bbb.mp4",
    "https://download.samplelib.com/mp4/sample-5s.mp4",
    "https://www.learningcontainer.com/wp-content/uploads/2020/05/sample-mp4-file.mp4",
)


class RemoteMediaFetcher:
    """Скачивает изображения и видео с бесплатных публичных API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        proxy: str | None = None,
    ) -> None:
        self._session = session
        self._proxy = proxy

    def _request_kwargs(self) -> dict[str, str]:
        if self._proxy:
            return {"proxy": self._proxy}
        return {}

    async def download_dog_image(self, destination: Path) -> None:
        """Сохраняет случайное фото собаки (dog.ceo).

        :param destination: Путь для записи файла.
        :raises aiohttp.ClientError: Ошибка HTTP или сети.
        """
        logger.info("Запрос фото собаки (dog.ceo)")
        async with self._session.get(
            DOG_IMAGE_API,
            **self._request_kwargs(),
        ) as response:
            response.raise_for_status()
            payload = await response.json()
        image_url = str(payload["message"])
        await self._download_binary(image_url, destination, source="dog.ceo")

    async def download_cat_image(self, destination: Path) -> None:
        """Сохраняет случайное фото кота (thecatapi.com) или fallback на dog.ceo.

        :param destination: Путь для записи файла.
        :raises aiohttp.ClientError: Ошибка HTTP или сети, если оба источника недоступны.
        """
        logger.info("Запрос фото кота (thecatapi.com)")
        try:
            async with self._session.get(
                CAT_IMAGE_API,
                **self._request_kwargs(),
            ) as response:
                response.raise_for_status()
                payload = await response.json()
            image_url = str(payload[0]["url"])
            await self._download_binary(
                image_url,
                destination,
                source="thecatapi.com",
            )
        except Exception as exc:
            logger.warning(
                "thecatapi.com недоступен (%s), используем dog.ceo вместо кота",
                exc,
            )
            await self.download_dog_image(destination)

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
