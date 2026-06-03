import argparse
import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def _parse_cors_origins(value: str | None) -> list[str]:
    from api.cors_origins import DEFAULT_CORS_ALLOW_ORIGINS

    if value is None or not value.strip() or value.strip() == "*":
        return list(DEFAULT_CORS_ALLOW_ORIGINS)
    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
    return origins or list(DEFAULT_CORS_ALLOW_ORIGINS)


def _run_api() -> None:
    import uvicorn

    from api.server import create_server

    database_url = os.environ["DATABASE_URL"]
    jwt_secret_key = os.environ["JWT_SECRET_KEY"]
    api_host = os.environ.get("API_HOST", "0.0.0.0")
    api_port = int(os.environ.get("API_PORT", "8000"))
    cors_origins = _parse_cors_origins(os.environ.get("CORS_ALLOW_ORIGINS"))
    s3_bucket = os.environ["S3_BUCKET"]
    jwt_expire_minutes = int(os.environ.get("JWT_EXPIRE_MINUTES", "60"))
    jwt_refresh_expire_days = int(os.environ.get("JWT_REFRESH_EXPIRE_DAYS", "7"))
    aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    aws_region = os.environ.get("AWS_REGION", "us-east-1")
    aws_endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
    aws_public_endpoint_url = os.environ.get("AWS_PUBLIC_ENDPOINT_URL")
    redis_url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    yookassa_shop_id = os.environ["YOOKASSA_SHOP_ID"]
    yookassa_secret_key = os.environ["YOOKASSA_SECRET_KEY"]
    yookassa_webhook_ip_check_enabled = os.environ.get(
        "YOOKASSA_WEBHOOK_IP_CHECK",
        "true",
    ).lower() not in {"0", "false", "no", "off"}

    app = create_server(
        database_url=database_url,
        jwt_secret_key=jwt_secret_key,
        cors_allow_origins=cors_origins,
        s3_bucket=s3_bucket,
        yookassa_shop_id=yookassa_shop_id,
        yookassa_secret_key=yookassa_secret_key,
        jwt_expire_minutes=jwt_expire_minutes,
        jwt_refresh_expire_days=jwt_refresh_expire_days,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_region=aws_region,
        aws_endpoint_url=aws_endpoint_url,
        aws_public_endpoint_url=aws_public_endpoint_url,
        redis_url=redis_url,
        yookassa_webhook_ip_check_enabled=yookassa_webhook_ip_check_enabled,
    )
    uvicorn.run(app, host=api_host, port=api_port)


async def _run_billing_renew(once: bool) -> None:
    import aiohttp
    from sqlalchemy.ext.asyncio import create_async_engine

    from billing.yookassa_client import YooKassaClient
    from broker.subscription_renewal_worker import SubscriptionRenewalWorker

    database_url = os.environ["DATABASE_URL"]
    yookassa_shop_id = os.environ["YOOKASSA_SHOP_ID"]
    yookassa_secret_key = os.environ["YOOKASSA_SECRET_KEY"]
    interval = float(os.environ.get("BILLING_RENEW_INTERVAL_SECONDS", "3600"))

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session = aiohttp.ClientSession()
    gateway = YooKassaClient(session, yookassa_shop_id, yookassa_secret_key)
    worker = SubscriptionRenewalWorker(engine, gateway, interval)
    try:
        if once:
            await worker.run_once()
        else:
            await worker.run()
    finally:
        await session.close()
        await engine.dispose()


async def _run_billing_sync(once: bool) -> None:
    import aiohttp
    from sqlalchemy.ext.asyncio import create_async_engine

    from billing.yookassa_client import YooKassaClient
    from broker.payment_status_sync_worker import PaymentStatusSyncWorker

    database_url = os.environ["DATABASE_URL"]
    yookassa_shop_id = os.environ["YOOKASSA_SHOP_ID"]
    yookassa_secret_key = os.environ["YOOKASSA_SECRET_KEY"]
    interval = float(os.environ.get("BILLING_SYNC_INTERVAL_SECONDS", "300"))

    engine = create_async_engine(database_url, pool_pre_ping=True)
    session = aiohttp.ClientSession()
    gateway = YooKassaClient(session, yookassa_shop_id, yookassa_secret_key)
    worker = PaymentStatusSyncWorker(engine, gateway, interval)
    try:
        if once:
            await worker.run_once()
        else:
            await worker.run()
    finally:
        await session.close()
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Very English backend")
    parser.add_argument(
        "command",
        nargs="?",
        default="api",
        choices=["api", "billing-renew", "billing-sync-payments"],
        help="Режим запуска (по умолчанию: api)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Выполнить одну итерацию worker и завершить работу",
    )
    args = parser.parse_args()

    if args.command == "api":
        _run_api()
    elif args.command == "billing-renew":
        asyncio.run(_run_billing_renew(args.once))
    elif args.command == "billing-sync-payments":
        asyncio.run(_run_billing_sync(args.once))


if __name__ == "__main__":
    main()
