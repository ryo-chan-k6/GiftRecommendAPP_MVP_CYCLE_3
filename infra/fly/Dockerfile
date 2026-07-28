# Reco (apps/reco) image for Fly.io
# Build context: repository root (see infra/fly/README.md)
# python: apps/reco/pyproject.toml requires-python >=3.14

FROM python:3.14-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/

WORKDIR /app

RUN apt-get update \
  && apt-get install -y --no-install-recommends ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY apps/reco/pyproject.toml apps/reco/uv.lock apps/reco/README.md ./
COPY apps/reco/src ./src

# Project install は hatch path 都合で skip。local と同様 --app-dir src で起動する。
RUN uv sync --frozen --no-dev --no-install-project

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "reco.api.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
