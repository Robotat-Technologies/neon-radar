# The NeonRadar API image (PHASE-1.md M1.9e). Build with the repository root as context:
#   docker compose --profile app build api
# The root .dockerignore keeps .env, .git, data/cache and local virtual environments out.
# Base: uv 0.13.4 on Python 3.14.8, Debian trixie; the tag is pinned by its index digest.
FROM ghcr.io/astral-sh/uv:python3.14-trixie@sha256:81ff59d597a2483d6dfa5a65bf4e021f6e9df8aa68dd6fa3ab5052d2d76fc97b

# PyICU (required by FollowTheMoney) builds from source against the ICU headers.
RUN apt-get update \
    && apt-get install -y --no-install-recommends pkg-config libicu-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Third-party dependencies first, from the lock file and the workspace manifests only, so that a
# code change does not rebuild PyICU; uv's build cache keeps the PyICU wheel when the lock changes.
COPY pyproject.toml uv.lock ./
COPY api/pyproject.toml api/
COPY cli/pyproject.toml cli/
COPY contracts/pyproject.toml contracts/
COPY copilot/pyproject.toml copilot/
COPY detect/pyproject.toml detect/
COPY graph/pyproject.toml graph/
COPY ingest/pyproject.toml ingest/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --package neonradar-api --no-install-workspace

# Then the repository. Workspace members stay editable, so contracts/, detect/ and docs/ files
# resolve as in development (NR_REPO_ROOT).
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --package neonradar-api

# At run time uv only starts the installed environment and needs no cache.
ENV NR_REPO_ROOT=/app \
    UV_NO_CACHE=1

# The files stay owned by root and read-only for the user that runs the API.
RUN useradd --uid 10001 --user-group --no-create-home --home-dir /nonexistent \
    --shell /usr/sbin/nologin neonradar
USER 10001:10001

EXPOSE 8000
# All interfaces inside the container; Compose publishes the port on 127.0.0.1 only.
CMD ["uv", "run", "--no-sync", "uvicorn", "neonradar_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
