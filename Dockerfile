FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Run as a normal user, not root.
RUN useradd --create-home --uid 10001 app
WORKDIR /app

# Install the package (with the api, db and gemini extras) from source.
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install ".[api,db,gemini]"

COPY alembic.ini ./
COPY migrations ./migrations

USER app
EXPOSE 8000

# Apply database migrations, then start the server.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn llmguard.api.main:build_app --factory --host 0.0.0.0 --port 8000"]
