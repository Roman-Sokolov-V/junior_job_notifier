# Python 3.14 + room for torch/sentence-transformers; Playwright needs OS libs for Chromium.
FROM python:3.14.5-bookworm

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependency layer (cache-friendly)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen \
    && uv run playwright install-deps chromium \
    && uv run playwright install chromium

#RUN chmod +x docker/entrypoint.sh

#ENTRYPOINT ["./docker/entrypoint.sh"]
#CMD ["uv", "run", "run.py"]
