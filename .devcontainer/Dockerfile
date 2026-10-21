# NeonRadar devcontainer (PHASE-1.md M1.5): Python 3.14 and uv 0.13 on Debian 13, with ICU for PyICU.
# Node 24, gh and Claude Code come from the features in devcontainer.json (pinned in
# devcontainer-lock.json). The base image is pinned by digest (amd64 and arm64); Dependabot
# proposes updates.
FROM ghcr.io/astral-sh/uv:0.13-python3.14-trixie@sha256:81ff59d597a2483d6dfa5a65bf4e021f6e9df8aa68dd6fa3ab5052d2d76fc97b
RUN apt-get update \
 && apt-get install -y --no-install-recommends pkg-config libicu-dev build-essential git make jq ca-certificates \
 && rm -rf /var/lib/apt/lists/*
# Docker Desktop shows the bind-mounted checkout's top folder as owned by root, and git then
# refuses the repository ("dubious ownership").
RUN git config --system --add safe.directory /workspaces/neonradar
RUN useradd --create-home --shell /bin/bash --uid 1000 dev \
 && mkdir -p /home/dev/.claude \
 && chown dev:dev /home/dev/.claude
USER dev
# The virtual environment lives in the container, not in the bind-mounted checkout: it never
# replaces a host's .venv (macOS or Windows binaries) and stays off the slow bind mount.
ENV UV_PROJECT_ENVIRONMENT=/home/dev/.venv \
    PATH=/home/dev/.venv/bin:$PATH
WORKDIR /workspaces/neonradar
