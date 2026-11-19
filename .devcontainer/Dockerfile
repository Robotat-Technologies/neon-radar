# Use the same pinned Node and Python images as the application.
FROM node:24.22.1-trixie-slim@sha256:43b9ba1142b8dcf33fa8f922ca1be85714adc444e0586c7cf7726daaeabc1bea AS node

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

COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules

RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && useradd --create-home --shell /bin/bash --uid 1000 dev

ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PYTHONUNBUFFERED=1

WORKDIR /workspaces/neonradar

USER dev
CMD ["sleep", "infinity"]