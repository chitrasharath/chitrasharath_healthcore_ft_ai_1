FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY services/api/pyproject.toml services/api/uv.lock ./services/api/
COPY packages/shared/python ./packages/shared/python/

WORKDIR /app/services/api
RUN uv sync --frozen --no-install-project --extra dev \
    && uv run python -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True)"

# Ensure container processes find the downloaded tokenizers
ENV NLTK_DATA=/root/nltk_data

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
