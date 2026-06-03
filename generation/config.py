from dataclasses import dataclass


@dataclass
class GenerationConfig:
    """Параметры подключения для генерации данных."""

    database_url: str
    s3_bucket: str
    aws_access_key_id: str | None
    aws_secret_access_key: str | None
    aws_region: str
    aws_endpoint_url: str | None
    aws_public_endpoint_url: str | None
    http_proxy: str | None = None
