# NeonRadar devcontainer (PHASE-1.md M1.5). Images pinned by digest; gh comes from the feature in
# devcontainer-lock.json. Node.js 24 comes from the official image: node, npm, npx and corepack only.
FROM docker.io/library/node:24-trixie-slim@sha256:43b9ba1142b8dcf33fa8f922ca1be85714adc444e0586c7cf7726daaeabc1bea AS node

FROM ghcr.io/astral-sh/uv:0.13-python3.14-trixie@sha256:81ff59d597a2483d6dfa5a65bf4e021f6e9df8aa68dd6fa3ab5052d2d76fc97b
RUN apt-get update \
 && apt-get install -y --no-install-recommends pkg-config libicu-dev build-essential git make jq ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && ln -s ../lib/node_modules/corepack/dist/corepack.js /usr/local/bin/corepack
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
