import os
import tempfile
from pathlib import Path

from fastapi import UploadFile


async def save_upload_to_temp(upload: UploadFile) -> Path:
    """Сохраняет загруженный файл во временный путь на диске.

    :param upload: Файл из multipart-запроса.
    :return: Путь к временному файлу (нужно удалить после использования).
    """
    suffix = Path(upload.filename or "upload").suffix
    fd, temp_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    path = Path(temp_path)
    content = await upload.read()
    path.write_bytes(content)
    return path
