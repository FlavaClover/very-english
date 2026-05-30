import os
from logging.config import fileConfig

from sqlalchemy import pool
from dotenv import load_dotenv
from sqlalchemy import engine_from_config
from alembic.script import ScriptDirectory

from alembic import context

load_dotenv()

# Объект конфигурации Alembic, даёт доступ к значениям из .ini.
config = context.config

if 'PYTEST_CURRENT_TEST' not in os.environ:
    url = os.getenv('DATABASE_URL', config.get_main_option('sqlalchemy.url'))
    if url is None:
        raise RuntimeError('DATABASE_URL is not configured for alembic')
    if url.startswith('postgresql://') and 'psycopg' not in url:
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)

    config.set_main_option('sqlalchemy.url', url)

# Настройка логирования из конфига.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Для поддержки autogenerate добавьте сюда MetaData модели.
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# Другие опции из конфига при необходимости:
# my_important_option = config.get_main_option("my_important_option")

script_directory = ScriptDirectory.from_config(config)


def _generate_next_revision_id():
    head = script_directory.get_current_head()
    if head is None:
        return '0001'

    prefix = head.split('_')[0]
    try:
        number = int(prefix)
    except (TypeError, ValueError):
        number = 0

    return '{:04d}'.format(number + 1)


def process_revision_directives(context, revision, directives):
    script = directives[0]
    # Для старых версий Alembic флага is_branch_point может не быть,
    # а ветвление нам сейчас не нужно — просто генерируем последовательный id.
    script.rev_id = _generate_next_revision_id()


def run_migrations_offline():
    """Запуск миграций в режиме 'offline'.

    Контекст настраивается только URL без создания Engine.
    Вызовы context.execute() выводят SQL в скрипт.
    """
    url = config.get_main_option('sqlalchemy.url')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Запуск миграций в режиме 'online'.

    Создаётся Engine и соединение связывается с контекстом.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
