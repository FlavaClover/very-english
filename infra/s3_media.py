from os import PathLike
from pathlib import Path

import aioboto3
import redis.asyncio as redis

from core.tutors import Media


class S3Media(Media):
    def __init__(
        self,
        session: aioboto3.Session,
        bucket: str,
        endpoint_url: str | None = None,
        public_endpoint_url: str | None = None,
        presigned_expire_seconds: int = 3600,
        redis_client: redis.Redis | None = None,
        url_cache_ttl_seconds: int = 3600,
        url_cache_key_prefix: str = "media:url:",
    ) -> None:
        self._session = session
        self._bucket = bucket
        self._endpoint_url = endpoint_url
        self._public_endpoint_url = public_endpoint_url or endpoint_url
        self._presigned_expire_seconds = presigned_expire_seconds
        self._redis = redis_client
        self._url_cache_ttl = url_cache_ttl_seconds
        self._url_cache_key_prefix = url_cache_key_prefix

    def _url_cache_key(self, name: str) -> str:
        return f"{self._url_cache_key_prefix}{name}"

    async def add(self, value: Path | PathLike | str, name: str) -> None:
        if self._redis is not None:
            await self._redis.delete(self._url_cache_key(name))
        path = Path(value)
        async with self._client() as client:
            await client.put_object(
                Bucket=self._bucket,
                Key=name,
                Body=path.read_bytes(),
            )

    async def remove(self, name: str) -> None:
        if self._redis is not None:
            await self._redis.delete(self._url_cache_key(name))
        async with self._client() as client:
            await client.delete_object(
                Bucket=self._bucket,
                Key=name,
            )

    async def url(self, name: str) -> str:
        if self._redis is not None:
            cache_key = self._url_cache_key(name)
            cached = await self._redis.get(cache_key)
            if cached is not None:
                return str(cached)
            url = await self._generate_presigned_url(name)
            await self._redis.setex(cache_key, self._url_cache_ttl, url)
            return url
        return await self._generate_presigned_url(name)

    async def _generate_presigned_url(self, name: str) -> str:
        async with self._client(self._public_endpoint_url) as client:
            return await client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self._bucket, "Key": name},
                ExpiresIn=self._presigned_expire_seconds,
            )

    def _client(self, endpoint_url: str | None = None):
        resolved = self._endpoint_url if endpoint_url is None else endpoint_url
        if resolved:
            return self._session.client("s3", endpoint_url=resolved)
        return self._session.client("s3")
