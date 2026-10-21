# The NeonRadar UI image (PHASE-1.md M1.9e). Build with the repository root as context
# (`context: .`, `dockerfile: ui/Dockerfile`), so the root .dockerignore keeps a host's
# ui/node_modules and ui/dist out. Both base images are pinned by tag and index digest.

# Node 24.22.1 LTS, Debian trixie slim.
FROM node:24.22.1-trixie-slim@sha256:43b9ba1142b8dcf33fa8f922ca1be85714adc444e0586c7cf7726daaeabc1bea AS build
WORKDIR /src/ui
COPY ui/package.json ui/package-lock.json ./
# No dependency in the lock file needs an install script on Linux (only fsevents, macOS).
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY ui/ ./
RUN npm run build

# nginx 1.30.6 (stable), Alpine.
FROM nginx:1.30.6-alpine@sha256:970364228b1e4f932abc22d321932816782cca8a20b85a77552a7cfe9acfb3b5
COPY ui/nginx.conf /etc/nginx/nginx.conf
RUN rm -f /etc/nginx/conf.d/default.conf
COPY --from=build /src/ui/dist /usr/share/nginx/html
# The image's unprivileged nginx user; it listens on 8080, so it needs no capability.
USER nginx
EXPOSE 8080
