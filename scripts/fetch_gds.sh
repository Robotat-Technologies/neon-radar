#!/usr/bin/env bash
# Download the pinned Neo4j Graph Data Science (GDS) jar once (PHASE-1.md M1.4).
# The neo4j:5.26.32-community image has no GDS jar, and its entrypoint would download one from
# graphdatascience.ninja on every start. This script is the explicit, one-time network step
# instead (guardrail G3): `make plugins` runs it; `make up` only runs `--check`, offline.
set -euo pipefail

GDS_VERSION="2.13.4"
GDS_SHA256="10e072f73992224f1159f246c9d6a89da5f3b3434aeffa5be42647edda13a8d8"
GDS_URL="https://github.com/neo4j/graph-data-science/releases/download/${GDS_VERSION}/neo4j-graph-data-science-${GDS_VERSION}.jar"

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dir="$root/data/cache/neo4j-plugins"
jar="$dir/neo4j-graph-data-science-${GDS_VERSION}.jar"

sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1
}
verified() { [ -f "$jar" ] && [ "$(sha256 "$jar")" = "$GDS_SHA256" ]; }

if [ "${1:-}" = "--check" ]; then
  verified && exit 0
  echo "The GDS plugin jar is missing or does not match its pinned SHA-256:" >&2
  echo "  ${jar#"$root"/}" >&2
  echo "Run 'make plugins' once (it downloads GDS ${GDS_VERSION} from github.com), then 'make up'." >&2
  exit 1
fi

if verified; then
  echo "GDS ${GDS_VERSION} is already in ${jar#"$root"/} (SHA-256 verified)."
  exit 0
fi
mkdir -p "$dir"
tmp="$(mktemp "$dir/.download.XXXXXX")"
trap 'rm -f "$tmp"' EXIT
echo "Downloading GDS ${GDS_VERSION} from github.com (about 64 MB) ..."
curl --fail --silent --show-error --location --retry 3 --connect-timeout 20 --max-time 900 \
  --output "$tmp" "$GDS_URL"
actual="$(sha256 "$tmp")"
if [ "$actual" != "$GDS_SHA256" ]; then
  echo "SHA-256 mismatch for $GDS_URL: expected $GDS_SHA256, got $actual. Nothing installed." >&2
  exit 1
fi
chmod 0644 "$tmp" # the container's neo4j user reads it through a read-only bind mount
mv "$tmp" "$jar"
trap - EXIT
echo "Installed ${jar#"$root"/} (SHA-256 verified)."
