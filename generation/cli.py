import argparse
import asyncio
import logging
import os
import sys

import aiohttp
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from generation.config import GenerationConfig
from generation.proxy import mask_proxy_url, resolve_http_proxy
from generation.seeder import GeneratedAccount, GenerationRunner

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Генерация тегов, пользователей и туторов для локальной разработки.",
    )
    parser.add_argument(
        "--tags",
        type=int,
        default=15,
        metavar="N",
        help="Сколько тегов создать (по умолчанию: 15)",
    )
    parser.add_argument(
        "--users",
        type=int,
        default=5,
        metavar="N",
        help="Сколько обычных пользователей (по умолчанию: 5)",
    )
    parser.add_argument(
        "--tutors-base",
        type=int,
        default=3,
        metavar="N",
        help="Сколько туторов с подпиской BASE (по умолчанию: 3)",
    )
    parser.add_argument(
        "--tutors-pro",
        type=int,
        default=2,
        metavar="N",
        help="Сколько туторов с подпиской PRO (по умолчанию: 2)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Подробные логи (уровень DEBUG)",
    )
    parser.add_argument(
        "--proxy",
        metavar="URL",
        default=None,
        help=(
            "HTTP(S)-прокси для API медиа (иначе GENERATION_HTTP_PROXY, "
            "HTTPS_PROXY или HTTP_PROXY из .env)"
        ),
    )
    return parser


def load_config(cli_proxy: str | None = None) -> GenerationConfig:
    database_url = os.environ.get("DATABASE_URL")
    s3_bucket = os.environ.get("S3_BUCKET")
    if not database_url:
        raise SystemExit("Не задана переменная окружения DATABASE_URL")
    if not s3_bucket:
        raise SystemExit("Не задана переменная окружения S3_BUCKET")
    return GenerationConfig(
        database_url=database_url,
        s3_bucket=s3_bucket,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        aws_region=os.environ.get("AWS_REGION", "us-east-1"),
        aws_endpoint_url=os.environ.get("AWS_ENDPOINT_URL"),
        aws_public_endpoint_url=os.environ.get("AWS_PUBLIC_ENDPOINT_URL"),
        http_proxy=resolve_http_proxy(cli_proxy),
    )


def print_accounts_table(accounts: list[GeneratedAccount]) -> None:
    console = Console()
    table = Table(
        title="Сгенерированные аккаунты",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Имя", style="white")
    table.add_column("Роль", style="green")
    table.add_column("Подписка", style="yellow")
    table.add_column("Статус тутора", style="magenta")
    table.add_column("Логин (email)", style="blue")
    table.add_column("Пароль", style="red")

    for account in accounts:
        table.add_row(
            account.full_name,
            account.role,
            account.subscription,
            account.tutor_status,
            account.login,
            account.password,
        )

    console.print(table)
    console.print(
        f"\n[bold]Всего аккаунтов:[/bold] {len(accounts)} "
        f"(пользователи + туторы BASE + туторы PRO)"
    )


def validate_counts(tags: int, users: int, tutors_base: int, tutors_pro: int) -> None:
    for name, value in (
        ("--tags", tags),
        ("--users", users),
        ("--tutors-base", tutors_base),
        ("--tutors-pro", tutors_pro),
    ):
        if value < 0:
            raise SystemExit(f"{name} не может быть отрицательным")


async def run_async(args: argparse.Namespace) -> int:
    validate_counts(args.tags, args.users, args.tutors_base, args.tutors_pro)
    config = load_config(cli_proxy=args.proxy)
    logger.info(
        "План генерации: тегов=%s, пользователей=%s, туторов BASE=%s, PRO=%s",
        args.tags,
        args.users,
        args.tutors_base,
        args.tutors_pro,
    )
    logger.info("БД: %s", _mask_database_url(config.database_url))
    logger.info("S3 bucket: %s", config.s3_bucket)
    if config.http_proxy:
        logger.info("HTTP-прокси: %s", mask_proxy_url(config.http_proxy))
    else:
        logger.warning(
            "HTTP-прокси не задан — API медиа могут быть недоступны в вашем регионе; "
            "укажите GENERATION_HTTP_PROXY в .env или --proxy"
        )
    runner = GenerationRunner(config)
    accounts = await runner.execute(
        tag_count=args.tags,
        user_count=args.users,
        tutors_base=args.tutors_base,
        tutors_pro=args.tutors_pro,
    )
    logger.info("Генерация завершена, вывод таблицы аккаунтов (%s шт.)", len(accounts))
    print_accounts_table(accounts)
    return 0


def _mask_database_url(url: str) -> str:
    if "@" not in url:
        return url
    prefix, rest = url.split("@", 1)
    if "://" in prefix:
        scheme, _ = prefix.split("://", 1)
        return f"{scheme}://***@{rest}"
    return f"***@{rest}"


def main(argv: list[str] | None = None) -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("aiobotocore").setLevel(logging.WARNING)
    try:
        exit_code = asyncio.run(run_async(args))
    except KeyboardInterrupt:
        logger.info("Прервано пользователем")
        exit_code = 130
    except (aiohttp.ClientError, TimeoutError, OSError) as exc:
        logger.error("Ошибка загрузки медиа: %s", exc)
        exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
