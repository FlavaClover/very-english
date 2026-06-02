from unittest.mock import AsyncMock, MagicMock

import pytest

from infra.s3_media import S3Media


def _redis_mock() -> AsyncMock:
    store: dict[str, str] = {}

    client = AsyncMock()

    async def get(key: str):
        return store.get(key)

    async def setex(key: str, ttl: int, value: str):
        store[key] = value

    async def delete(key: str):
        store.pop(key, None)

    client.get = AsyncMock(side_effect=get)
    client.setex = AsyncMock(side_effect=setex)
    client.delete = AsyncMock(side_effect=delete)
    return client


def _s3_client_mock() -> AsyncMock:
    client = AsyncMock()
    client.put_object = AsyncMock()
    client.delete_object = AsyncMock()
    client.generate_presigned_url = MagicMock(
        return_value="https://s3.test/photo.png?signed=1"
    )
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.mark.asyncio
async def test_s3_media_add_uploads_file(tmp_path):
    file_path = tmp_path / "photo.png"
    file_path.write_bytes(b"image-bytes")

    client = _s3_client_mock()
    session = MagicMock()
    session.client.return_value = client

    media = S3Media(session=session, bucket="test-bucket")
    await media.add(file_path, "photo.png")

    session.client.assert_called_once_with("s3")
    client.put_object.assert_awaited_once_with(
        Bucket="test-bucket",
        Key="photo.png",
        Body=b"image-bytes",
    )


@pytest.mark.asyncio
async def test_s3_media_remove_deletes_object():
    client = _s3_client_mock()
    session = MagicMock()
    session.client.return_value = client

    media = S3Media(session=session, bucket="test-bucket")
    await media.remove("photo.png")

    session.client.assert_called_once_with("s3")
    client.delete_object.assert_awaited_once_with(
        Bucket="test-bucket",
        Key="photo.png",
    )


@pytest.mark.asyncio
async def test_s3_media_url_uses_public_endpoint_for_presign():
    internal_client = _s3_client_mock()
    public_client = _s3_client_mock()
    public_client.generate_presigned_url = MagicMock(
        return_value="http://localhost:9000/test-bucket/photo.png?signed=1"
    )
    session = MagicMock()

    def client_factory(service_name: str, endpoint_url: str | None = None):
        if endpoint_url == "http://minio:9000":
            return internal_client
        if endpoint_url == "http://localhost:9000":
            return public_client
        raise AssertionError(f"unexpected endpoint_url: {endpoint_url!r}")

    session.client.side_effect = client_factory

    media = S3Media(
        session=session,
        bucket="test-bucket",
        endpoint_url="http://minio:9000",
        public_endpoint_url="http://localhost:9000",
        presigned_expire_seconds=3600,
    )
    url = await media.url("photo.png")

    assert url == "http://localhost:9000/test-bucket/photo.png?signed=1"
    public_client.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={"Bucket": "test-bucket", "Key": "photo.png"},
        ExpiresIn=3600,
    )
    internal_client.generate_presigned_url.assert_not_called()


@pytest.mark.asyncio
async def test_s3_media_url_generates_presigned_link():
    client = _s3_client_mock()
    session = MagicMock()
    session.client.return_value = client

    media = S3Media(
        session=session, bucket="test-bucket", presigned_expire_seconds=3600
    )
    url = await media.url("photo.png")

    assert url == "https://s3.test/photo.png?signed=1"
    client.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={"Bucket": "test-bucket", "Key": "photo.png"},
        ExpiresIn=3600,
    )


@pytest.mark.asyncio
async def test_s3_media_url_caches_in_redis():
    redis_client = _redis_mock()
    client = _s3_client_mock()
    session = MagicMock()
    session.client.return_value = client

    media = S3Media(
        session=session,
        bucket="test-bucket",
        redis_client=redis_client,
        url_cache_ttl_seconds=3600,
    )

    first = await media.url("photo.png")
    second = await media.url("photo.png")

    assert first == second == "https://s3.test/photo.png?signed=1"
    client.generate_presigned_url.assert_called_once()
    redis_client.setex.assert_awaited_once()


@pytest.mark.asyncio
async def test_s3_media_remove_invalidates_url_cache():
    redis_client = _redis_mock()
    client = _s3_client_mock()
    session = MagicMock()
    session.client.return_value = client

    media = S3Media(
        session=session,
        bucket="test-bucket",
        redis_client=redis_client,
        url_cache_ttl_seconds=3600,
    )

    await media.url("photo.png")
    await media.remove("photo.png")
    await media.url("photo.png")

    assert client.generate_presigned_url.call_count == 2
    redis_client.delete.assert_awaited()
