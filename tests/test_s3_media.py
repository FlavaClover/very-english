from unittest.mock import AsyncMock, MagicMock

import pytest

from infra.s3_media import S3Media


@pytest.mark.asyncio
async def test_s3_media_add_uploads_file(tmp_path):
    file_path = tmp_path / "photo.png"
    file_path.write_bytes(b"image-bytes")

    client = AsyncMock()
    client.put_object = AsyncMock()
    client.delete_object = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

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
    client = AsyncMock()
    client.put_object = AsyncMock()
    client.delete_object = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    session = MagicMock()
    session.client.return_value = client

    media = S3Media(session=session, bucket="test-bucket")
    await media.remove("photo.png")

    session.client.assert_called_once_with("s3")
    client.delete_object.assert_awaited_once_with(
        Bucket="test-bucket",
        Key="photo.png",
    )
