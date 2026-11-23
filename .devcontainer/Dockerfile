FROM ghcr.io/astral-sh/uv:python3.14-trixie@sha256:81ff59d597a2483d6dfa5a65bf4e021f6e9df8aa68dd6fa3ab5052d2d76fc97b

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        curl \
        git \
        jq \
        libicu-dev \
        make \
        openssl \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Use HTTP/1.1 and retry interrupted Node binary downloads.
RUN printf '%s\n' \
    '#!/bin/sh' \
    'for arg in "$@"; do' \
    '  case "$arg" in' \
    '    https://nodejs.org/dist/*/node-*-linux-*.tar.xz)' \
    '      exec /usr/bin/curl --http1.1 --retry 5 --retry-all-errors --retry-delay 3 "$@" ;;' \
    '  esac' \
    'done' \
    'exec /usr/bin/curl --http1.1 "$@"' \
    > /usr/local/bin/curl \
    && chmod +x /usr/local/bin/curl

RUN useradd --create-home --shell /bin/bash --uid 1000 dev \
    && mkdir -p /home/dev/.claude \
    && chown dev:dev /home/dev/.claude

# Allow Claude's installation script for root-run feature installation.
RUN printf '%s\n' \
    'allow-scripts=@anthropic-ai/claude-code' \
    'fetch-retries=5' \
    'fetch-timeout=300000' \
    'maxsockets=2' \
    >> /root/.npmrc
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1 \
    npm_config_include=optional

WORKDIR /workspaces/neonradar

USER dev
CMD ["sleep", "infinity"]
