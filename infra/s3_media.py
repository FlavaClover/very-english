from os import PathLike
from pathlib import Path

import aioboto3

from core.tutors import Media


class S3Media(Media):
    def __init__(
        self,
        session: aioboto3.Session,
        bucket: str,
    ) -> None:
        self._session = session
        self._bucket = bucket

    async def add(self, value: Path | PathLike | str, name: str) -> None:
        path = Path(value)
        async with self._session.client("s3") as client:
            await client.put_object(
                Bucket=self._bucket,
                Key=name,
                Body=path.read_bytes(),
            )

    async def remove(self, name: str) -> None:
        async with self._session.client("s3") as client:
            await client.delete_object(
                Bucket=self._bucket,
                Key=name,
            )
