FROM python:3.12-slim

# Install hledger
RUN apt-get update && \
    apt-get install -y --no-install-recommends hledger && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# Copy application code
COPY app.py hledger.py ./
COPY templates/ templates/
COPY static/ static/

RUN groupadd --gid 1000 appuser && \
    useradd --create-home --uid 1000 --gid 1000 appuser
USER appuser

EXPOSE 8000

ENV UV_NO_SYNC=1

CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
