FROM python:3.14

# Прокси только на этапе сборки (apt, pip, poetry). Передавайте через build-arg или env хоста.
ARG HTTP_PROXY=
ARG HTTPS_PROXY=
ARG NO_PROXY=
ARG http_proxy=
ARG https_proxy=
ARG no_proxy=

ENV HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY} \
    http_proxy=${http_proxy} \
    https_proxy=${https_proxy} \
    no_proxy=${no_proxy}

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

ENV HTTP_PROXY= \
    HTTPS_PROXY= \
    NO_PROXY= \
    http_proxy= \
    https_proxy= \
    no_proxy=

EXPOSE 8000

CMD ["python", "main.py", "api"]
