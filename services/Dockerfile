FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY services/api/pyproject.toml services/api/uv.lock ./services/api/
COPY packages/shared/python ./packages/shared/python/

WORKDIR /app/services/api
RUN uv sync --frozen --no-install-project --extra dev

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
