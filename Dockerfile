FROM python:3.14

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.1.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && pip install --no-cache-dir "poetry==${POETRY_VERSION}" \
    && apt-get purge -y curl \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root

COPY . .

EXPOSE 8000

CMD ["python", "main.py", "api"]
