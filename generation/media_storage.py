import logging
import tempfile
from pathlib import Path
from uuid import UUID

import aioboto3

from core.tutors import Media
from generation.remote_media import RemoteMediaFetcher
from infra.s3_media import S3Media

logger = logging.getLogger(__name__)


class GenerationMediaStorage:
    """Загружает медиа с внешних API в S3 и возвращает ключи объекта."""

    def __init__(
        self,
        media: Media,
        fetcher: RemoteMediaFetcher,
        temp_dir: Path,
    ) -> None:
        self._media = media
        self._fetcher = fetcher
        self._temp_dir = temp_dir

    @classmethod
    def from_config(
        cls,
        fetcher: RemoteMediaFetcher,
        bucket: str,
        aws_access_key_id: str | None,
        aws_secret_access_key: str | None,
        aws_region: str,
        aws_endpoint_url: str | None,
        aws_public_endpoint_url: str | None,
    ) -> "GenerationMediaStorage":
        session = aioboto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        media = S3Media(
            session=session,
            bucket=bucket,
            endpoint_url=aws_endpoint_url,
            public_endpoint_url=aws_public_endpoint_url,
        )
        temp_dir = Path(tempfile.mkdtemp(prefix="very-english-gen-"))
        logger.info("Временная директория для медиа: %s", temp_dir)
        return cls(media=media, fetcher=fetcher, temp_dir=temp_dir)

    async def upload_user_photo(self, user_id: UUID, use_cat: bool = False) -> str:
        key = f"users/{user_id}/avatar.jpg"
        source = "кот" if use_cat else "собака"
        logger.info("Аватар пользователя %s (%s)", user_id, source)
        path = self._temp_dir / f"{user_id}-avatar.jpg"
        if use_cat:
            await self._fetcher.download_cat_image(path)
        else:
            await self._fetcher.download_dog_image(path)
        await self._media.add(path, key)
        logger.info("Аватар загружен в S3: %s", key)
        return key

    async def upload_achievement_image(
        self,
        tutor_id: UUID,
        index: int,
        use_cat: bool,
    ) -> str:
        key = f"tutors/{tutor_id}/achievements/{index}.jpg"
        source = "кот" if use_cat else "собака"
        logger.info(
            "Достижение #%s тутора %s (%s)",
            index + 1,
            tutor_id,
            source,
        )
        path = self._temp_dir / f"{tutor_id}-ach-{index}.jpg"
        if use_cat:
            await self._fetcher.download_cat_image(path)
        else:
            await self._fetcher.download_dog_image(path)
        await self._media.add(path, key)
        logger.info("Достижение загружено в S3: %s", key)
        return key

    async def upload_visit_video(self, tutor_id: UUID) -> str:
        key = f"tutors/{tutor_id}/visit-video.mp4"
        logger.info("Видеовизитка тутора %s", tutor_id)
        path = self._temp_dir / f"{tutor_id}-visit.mp4"
        await self._fetcher.download_sample_video(path)
        await self._media.add(path, key)
        logger.info("Видеовизитка загружена в S3: %s", key)
        return key
