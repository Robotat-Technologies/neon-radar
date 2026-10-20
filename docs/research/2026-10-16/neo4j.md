# Neo4j research for NeonRadar phase 1

Scope: Neo4j Community Edition only (no Aura, no Enterprise), Docker Compose, laptop-first, Python backend. The project must be stable through 20 November 2026.

Research date: all facts below were checked on 16 October 2026 (written as "checked 2026-10-16"). Every fact carries the URL it was verified against. Where a fact could not be verified against a primary source it is marked UNVERIFIED. Source numbers in square brackets refer to the Sources list at the end; the URL is also given inline the first time it is used in a section.

Method note: neo4j.com, Docker Hub and GitHub pages were read through the research fetch tool; GitHub repositories (docker-neo4j, docs-operations, docs-cypher, apoc, graph-data-science, graph-data-science-client, neo4j-python-driver, neo4j-graphrag-python, testcontainers-python) were additionally cloned read-only and inspected at the commits noted in the Sources list; PyPI metadata was read from the PyPI JSON API; the testcontainers 4.15.0 wheel was downloaded from PyPI and inspected.

---

## 1. Release lines and Docker tags

### Release lines as of 16 October 2026

- Neo4j 5.26 is the Long-Term Support line and the last 5.x minor. Neo4j's LTS blog post says it is supported "until June 2028" with critical patches and security updates but no new features. Source: https://neo4j.com/blog/developer/neo4j-v5-lts-evolution/ [S1], checked 2026-10-16.
- The latest 5.26 patch is 5.26.32, released 9 October 2026 (5.26.31 on 22 September 2026, 5.26.30 on 26 August 2026). Source: https://neo4j.com/release-notes/database/ [S2] and https://neo4j.com/release-notes/database/neo4j-5-26-32/ [S3], checked 2026-10-16.
- Since January 2025 Neo4j Server uses calendar versioning YYYY.MM.PATCH; an optional fourth component "LTS" marks long-term-support releases. "There is a new LTS version of Neo4j roughly every 18 to 24 months." Source: https://neo4j.com/docs/upgrade-migration-guide/current/ [S4], checked 2026-10-16.
- Calendar releases that exist: 2025.01 through 2025.12 and 2026.01 through 2026.09. The newest is 2026.09.0 (21 September 2026). None of the calendar releases so far is an LTS; each is superseded by the next one (endoflife.date lists each 2025.x/2026.x line as supported only until the following release). Source: https://endoflife.date/neo4j [S5] (third-party tracker, cross-checked with [S2]), checked 2026-10-16.
- A "2026.LTS" is coming but not yet released or dated: the 2026.09.0 release notes contain an "advance notice of post-2026.LTS changes" (query log default switching to JSON, removal of the High_limit store format in the release after the next LTS) without naming the version or month. Source: https://neo4j.com/release-notes/database/neo4j-2026-09-0/ [S6], checked 2026-10-16. Exact version number and date of the 2026 LTS: UNVERIFIED (not published anywhere I could find on 2026-10-16).
- The docs source for the Operations Manual is already versioned "2026.10" (antora.yml in neo4j/docs-operations, commit 8b6a119, 15 October 2026), so a 2026.10.0 release is imminent, most likely in late October 2026. Source: [S7] (repo clone), checked 2026-10-16. Release date of 2026.10.0: UNVERIFIED.
- Java: Neo4j 2025.01 and later require Java 21 ("Java 17 is no longer supported in Neo4j 2025.01"); Java 25 is supported from 2025.10. Source: https://neo4j.com/docs/upgrade-migration-guide/current/version-2025-2026/upgrade/ [S8], checked 2026-10-16. Neo4j 5.26 runs on Java 17 or 21 (GDS README compatibility matrix lists "GDS 2.13, Neo4j 5.26, Java 21 & Java 17"). Source: neo4j/graph-data-science README.adoc [S9], checked 2026-10-16.

### Community Edition availability

- Every release line above ships a Community Edition. The official Docker image publishes a `-community` variant for 4.4.x, 5.26.x, 2025.x and 2026.x (see tag list below). Source: Docker Hub API https://hub.docker.com/v2/repositories/library/neo4j/tags?page_size=100&name=community [S10], checked 2026-10-16.
- Community Edition is "open source under GPLv3" per the edition comparison table in the Operations Manual introduction. Source: https://raw.githubusercontent.com/neo4j/docs-operations/dev/modules/ROOT/pages/introduction.adoc [S11], checked 2026-10-16.
- Community versus Enterprise differences that matter for this project (from the same edition table [S11], checked 2026-10-16):
  - Community has: Cypher, slotted runtime, Browser, Cypher Shell, Bolt, all drivers, APOC Core, GDS Community, GenAI plugin, native label indexes, composite indexes, full-text indexes, vector indexes, property uniqueness constraints, offline full import, offline dump, Aligned store format.
  - Enterprise only: pipelined and parallel Cypher runtimes, Block store format, property existence constraints, property type constraints, node and relationship key constraints, incremental import, online backup, multiple user databases, clustering, RBAC, Bloom, GDS Enterprise, Prometheus metrics, Ops Manager.

### Docker Hub tags (official `neo4j` image)

Verified via the Docker Hub tags API on 2026-10-16 [S10, S12, S13]:

- Tag naming: no suffix or `-community` means Community Edition (`neo4j:2026.07.1` is Community). `-enterprise` is Enterprise. Base OS suffixes: `-trixie` (debian:trixie-slim, Debian 13, the default when no suffix is given) and `-ubi10` (Red Hat UBI 10). Debian 13 and UBI 10 images exist from 2026.01.0 onward; from 2026.05 the older bullseye and ubi9 bases are no longer published. Source: https://neo4j.com/docs/operations-manual/current/docker/introduction/ [S14], checked 2026-10-16.
- Confirmed Community tags (last pushed dates from the API, checked 2026-10-16):
  - `neo4j:5.26.32-community` (2026-10-12), `neo4j:5.26.32-community-trixie`, `neo4j:5.26.32-community-ubi10`
  - `neo4j:5.26-community` (floating within 5.26.x, 2026-10-12), `neo4j:5-community`, `neo4j:5.26`, `neo4j:5`
  - `neo4j:2026.09.0-community` (2026-10-06), `neo4j:2026.09-community`, `neo4j:2026-community`, `neo4j:2026.09.0`, `neo4j:2026`
  - `neo4j:2026.08.1-community`, `neo4j:2026.07.1-community`, and the 2025.xx-community series (562 tags match "community" in total)
  - `neo4j:4.4.48-community`, `neo4j:4.4-community`
  - `neo4j:community` and `neo4j:latest` float to the newest calendar Community image (docker-library docs list `latest` as an alias of `2026.08.1-community-trixie` at the time the README was generated; the Docker Hub `latest` tag was re-pushed on 2026-09-16). Source: https://github.com/docker-library/docs/blob/master/neo4j/README.md [S15], checked 2026-10-16.
- All current tags are multi-arch: linux/amd64 and linux/arm64 (so Apple Silicon laptops run natively). Source: [S10], checked 2026-10-16.
- Base JDK inside the images: 5.x images copy the JDK from `eclipse-temurin:21`; calendar (2025/2026) images copy it from `eclipse-temurin:25`. Source: neo4j/docker-neo4j `docker-image-src/5/coredb/Dockerfile-trixie` and `docker-image-src/calver/coredb/Dockerfile-trixie` (commit fd9e4ec, 30 September 2026) [S16], checked 2026-10-16.
- The images contain `wget`, `jq`, `cypher-shell` and `neo4j-admin`; `curl` is installed during the build and then purged (Debian) or never installed (UBI). This matters for health checks (section 3). Source: same Dockerfiles [S16], checked 2026-10-16.

### Recommended tag: `neo4j:5.26.32-community`

Reasoning:

1. It is the current patch of the only LTS line. It gets security fixes until June 2028 [S1] but no feature changes, so nothing moves under the project between now and 20 November 2026.
2. Pinning the exact patch (not `5.26-community`) makes `docker compose pull` deterministic for every intern and for CI. Move to a newer 5.26.x patch deliberately, as a reviewed pull request.
3. The bundled plugin versions are fixed and known: Neo4j 5.26.32 ships APOC Core 5.26.32 (labs/apoc-5.26.32), Graph Data Science 2.13.14, GenAI plugin 5.26.32 and Browser 2026.10.08+0 inside the distribution. Source: [S3], checked 2026-10-16. With `NEO4J_PLUGINS` the image installs these bundled jars without any network download (section 2).
4. The calendar line is a moving target during the project window: 2026.10 is imminent (section 1), 2026.11 would land inside the window, and each calendar release is only supported until the next one [S5]. In addition the 2026.LTS is expected soon with post-LTS removals announced [S6]. Nothing in the calendar line is required for phase 1: quantified path patterns, SHORTEST, CALL IN (CONCURRENT) TRANSACTIONS, vector and full-text indexes all exist in 5.26 (sections 4 and 5).
5. Cost of this choice: no Cypher 25 (no SEARCH clause, no FOR or LET clauses, no map comprehension); vector and full-text search go through the `db.index.*` procedures, which is fine in Cypher 5. If the team wants Cypher 25 later, "Online upgrades from Neo4j 5.26 LTS to any Neo4j 2025-2026 version are supported" [S4].

If a calendar image is nonetheless chosen, pin `neo4j:2026.09.0-community` (not `2026.09-community`, not `2026-community`, never `latest`), and accept that its default database runs Cypher 25 (section 4).

---

## 2. Graph Data Science and APOC

### GDS versions and compatibility

- GDS versioning switched to calendar versions in spring 2026: GDS 2.26 pairs with Neo4j 2026.01, GDS 2.27 with 2026.02, then GDS 2026.03.0, 2026.04.0, 2026.05.0, 2026.06.0, 2026.07.0, 2026.08.1 and the latest GDS 2026.09.0 (released 21 September 2026, "compatible with Neo4j 2026.09", no functional changes listed). Source: https://neo4j.com/release-notes/gds/ [S17] and https://neo4j.com/release-notes/gds/graph-data-science-2026-09-0/ [S18], checked 2026-10-16.
- The GDS line for Neo4j 5.26 is GDS 2.13. Source: compatibility table at https://neo4j.com/docs/graph-data-science/current/installation/supported-neo4j-versions/ [S19] (lists 5.26 -> 2.13, 2025.01 -> 2.14 ... 2025.12.1 -> 2.25; the page has not been extended with 2026.x rows), checked 2026-10-16. The GDS README states the same: "GDS 2.13 | Neo4j 5.26 | Java 21 & Java 17" [S9].
- The exact GDS 2.13 patch bundled in Neo4j 5.26.32 is 2.13.14 (5.26.31 bundled 2.13.13). Source: [S3] and https://neo4j.com/release-notes/database/neo4j-5-26-31/ [S20], checked 2026-10-16.
- GDS is bundled: "Both Neo4j Community Edition (CE) and Enterprise Edition (EE) come with a range of pre-installed products, such as Gen AI, Bloom, and Graph Data Science in the products directory, and the APOC Core jar file in the labs directory." Source: neo4j/docs-operations `configuration/plugins.adoc` (served at https://neo4j.com/docs/operations-manual/current/configuration/plugins/) [S21], checked 2026-10-16. The GDS manual says the same for the server install: "The GDS plugin is bundled in the Community Edition distribution ... The plugin is always compatible with the server version it ships with." Source: https://neo4j.com/docs/graph-data-science/current/installation/neo4j-server/ [S22], checked 2026-10-16.
- GDS Python client (`graphdatascience` on PyPI): latest 2.2 (14 October 2026); 2.0 was released 18 September 2026. Requires Python >= 3.10 and `neo4j>=5.26.0,<7.0`. Source: PyPI JSON API https://pypi.org/pypi/graphdatascience/json [S23], checked 2026-10-16. Clients 2.1 to 2.3 support GDS server ">= 2.13, < 2.28, < 2026.10" and client 2.0 supports ">= 2.13, < 2.28, < 2026.9" (so GDS 2.13.14 on 5.26.32 is supported by all of them); all 2.x clients need driver ">= 5.26.0, < 7.0.0". Source: neo4j/graph-data-science-client `doc/modules/ROOT/pages/installation.adoc` (commit 4457aa6, 14 October 2026) [S24], checked 2026-10-16. The 2.x client dropped the 1.x API (snake_case endpoints, typed results, no `gds.alpha`/`gds.beta` prefixes, projection API changed). Source: `doc/modules/ROOT/pages/migration-from-1x.adoc` in the same repo [S24], checked 2026-10-16.

### Installing GDS in Docker

- Exact value: `NEO4J_PLUGINS='["graph-data-science"]'`. With APOC: `NEO4J_PLUGINS='["apoc", "graph-data-science"]'`. The value is a JSON array; the key `"gds"` is rejected ("gds" is not a known Neo4j plugin. Options are: apoc, apoc-extended, bloom, genai, graph-data-science, n10s). Source: https://neo4j.com/docs/graph-data-science/current/installation/installation-docker/ [S25] and https://neo4j.com/docs/operations-manual/current/docker/plugins/ [S26], checked 2026-10-16.
- What the entrypoint does (verified in `docker-image-src/calver/coredb/docker-entrypoint.sh` and the identical logic in `docker-image-src/5/coredb/`, plus `neo4j-plugins.json`, commit fd9e4ec [S16], checked 2026-10-16):
  - For `graph-data-science` the manifest entry is `location: /var/lib/neo4j/products/neo4j-graph-data-science-*.jar`, `versions: https://graphdatascience.ninja/versions.json`, `properties: dbms.security.procedures.unrestricted=gds.*`.
  - For `apoc` the entry is `location: /var/lib/neo4j/labs/apoc-*-core.jar`, `versions: https://neo4j.github.io/apoc/versions.json`, `properties: dbms.security.procedures.unrestricted=apoc.*`.
  - The script first checks the `location` glob inside the image; if the bundled jar exists it is copied to the plugins directory ("Installing Plugin ... from /var/lib/neo4j/products/..."), and the `properties` are appended to neo4j.conf. Only if no bundled jar exists does it download `versions.json` and pick the entry matching `neo4j --version`; when no entry matches it prints "No compatible ... plugin found for Neo4j <version>" and continues without the plugin.
  - Consequence: with `neo4j:5.26.32-community` the GDS and APOC installs are offline and deterministic (GDS 2.13.14, APOC 5.26.32). No `/plugins` download, no dependency on graphdatascience.ninja.
- The public GDS manifest at https://graphdatascience.ninja/versions.json [S27] was readable on 2026-10-16 but the fetched text ended at the entry for Neo4j 5.26.13 (GDS 2.13.7) with 2025.08.0 (GDS 2.21.0) as the highest calendar entry. Whether the live file contains entries for 5.26.14 to 5.26.32 or for 2026.x: UNVERIFIED (the fetch tool truncated at about 80 kB). This does not affect the Docker image because of the bundled-jar path above, but it does matter if you ever run a Neo4j version whose products directory lacks GDS.
- `dbms.security.procedures.unrestricted=gds.*` is required ("GDS accesses low-level components of Neo4j to maximise performance"); if `dbms.security.procedures.allowlist` is active, add `gds.*` to it too. `NEO4J_PLUGINS` sets the unrestricted setting automatically. Source: [S22], checked 2026-10-16.
- No licence acceptance variable is needed for GDS Community or APOC. `NEO4J_ACCEPT_LICENSE_AGREEMENT=yes` is for the Enterprise image only, and `NEO4J_gds_enterprise_license__file=/licenses/gds` plus a `/licenses` mount is for GDS Enterprise only. Source: [S25] and [S14], checked 2026-10-16.
- Verify: `RETURN gds.version()`, `CALL gds.list()`, `CALL gds.license.state()`. Source: https://neo4j.com/docs/graph-data-science/current/installation/ [S28], checked 2026-10-16.

### GDS Community Edition limitations

From the Editions section of the GDS manual introduction, https://neo4j.com/docs/graph-data-science/current/introduction/ [S29], checked 2026-10-16:

- Community Edition "Includes all algorithms", but "Limits the concurrency to maximum 4 CPU cores" and the model catalog holds at most 3 models; catalog operations are restricted to managing graphs and models.
- Enterprise only: unlimited concurrency, GDS write workloads in a cluster, capacity and load monitoring, graph backup and restore, Apache Arrow import and export, unlimited and shareable or persisted models, an "optimized graph implementation", and configurable defaults and limits.
- Practical effect for this project: on a 500k-node, 2M-relationship graph the algorithms the plan needs (WCC, Louvain or Leiden, PageRank, degree, node similarity) all run in CE; the 4-core cap slows them on an 8-core laptop but does not block them. Pass `concurrency: 4` explicitly so logs are quiet.
- macOS note from the GDS install page: add `server.jvm.additional=-Djol.skipHotspotSAAttach=true` (Docker env: `NEO4J_server_jvm_additional=-Djol.skipHotspotSAAttach=true`) when running the server natively on macOS. Source: [S28], checked 2026-10-16. Inside the Linux container this is not needed.

### GDS licence

- The GitHub repository neo4j/graph-data-science (openGDS) is licensed under GPLv3: LICENSE.txt says the software "is licensed under the GNU GENERAL PUBLIC LICENSE Version 3 to all third parties" unless a commercial agreement supersedes it; README.adoc: "OpenGDS is licensed under the GNU Public License version 3.0." Source: repo clone at commit 417d7ec (8 October 2026) [S9], checked 2026-10-16.
- The same README says the GDS build "as built and distributed by Neo4j includes the sources in this repository as well a suite of closed sources" and "is available to download and use under the constraints of its license". The licence text that governs the Neo4j-distributed Community jar (the one the Docker image installs) was not found as a primary document: UNVERIFIED. For an open-source project that only runs GDS inside a user's container and does not redistribute the jar this is a usage question, not a redistribution question, but the maintainers should read the licence file shipped inside the GDS jar or distribution before claiming anything in the README.

### APOC Core

- Versioning: APOC Core versions follow the Neo4j version ("Make sure that the year and month of the APOC version match those of the Neo4j version"; for 5.x the major.minor must match). The current APOC Core manual version is 2026.09 and the version switcher also offers 5.26 (LTS). Source: https://neo4j.com/docs/apoc/current/installation/ [S30] and https://neo4j.com/docs/apoc/current/ [S31], checked 2026-10-16.
- The APOC manifest https://neo4j.github.io/apoc/versions.json [S32] maps Neo4j 5.26.32 -> apoc-5.26.32-core.jar, 5.26.31 and 5.26.30 -> 5.26.32, 2026.08.1 -> 2026.08.1, and 2026.09.0 -> apoc-2026.09.0-core.jar (highest entry). Checked 2026-10-16.
- Docker: `NEO4J_PLUGINS='["apoc"]'` (the APOC manual warns this convenience path is "for development, not production"; for production mount the jar at `/plugins`). The bundled jar in the image is used first (see above). Source: [S30] and [S16], checked 2026-10-16.
- APOC settings go in `apoc.conf` (same folder as neo4j.conf) or environment variables; "APOC config settings are no longer supported in the neo4j.conf file" in Neo4j 5+, and environment variables override apoc.conf. The APOC manual's Docker examples use `-e NEO4J_apoc_export_file_enabled=true -e NEO4J_apoc_import_file_enabled=true -e NEO4J_apoc_import_file_use__neo4j__config=true`. Defaults: `apoc.import.file.enabled=false`, `apoc.export.file.enabled=false`, `apoc.import.file.use_neo4j_config=true`. Source: https://neo4j.com/docs/apoc/current/config/ [S33] and [S30], checked 2026-10-16.
- Licence: APOC Core is Apache License 2.0 (LICENSE file in neo4j/apoc, commit 4288f52, 15 October 2026) [S34], checked 2026-10-16. "APOC Core is officially supported by Neo4j"; "APOC Extended is not supported by Neo4j and is maintained by members of the community." Source: https://neo4j.com/docs/apoc/current/introduction/ [S35], checked 2026-10-16.
- `apoc.periodic.iterate` is in APOC Core (listed in the Core manual's apoc.periodic namespace together with commit, countdown, list, repeat, submit, truncate, cancel). Source: https://neo4j.com/docs/apoc/current/overview/apoc.periodic/ [S36], checked 2026-10-16.
- Surprise: the procedure page states "As of Neo4j 2026.04 and Cypher 25, apoc.periodic.iterate is deprecated" with the replacement "CALL {...} IN CONCURRENT TRANSACTIONS". Source: https://neo4j.com/docs/apoc/current/overview/apoc.periodic/apoc.periodic.iterate/ [S37] and https://neo4j.com/docs/apoc/current/deprecations-and-additions/ [S38], checked 2026-10-16. The deprecation applies to Cypher 25 on 2026.04+; on Neo4j 5.26 (Cypher 5 only) `apoc.periodic.iterate` is fully supported. Also from [S38]: "Any changes to APOC in future releases (APOC 2025.07+) are only compatible with Cypher 25", and large groups of APOC functions (apoc.coll.*, apoc.text.*, apoc.date.*, apoc.create.*, apoc.do.when and friends) are deprecated in Cypher 25 in favour of Cypher built-ins that do not exist in 5.26. A GraphAcademy post (14 July 2026) walks through the migration: https://graphacademy.neo4j.com/blog/replace-apoc-periodic-iterate-with-call-in-transactions [S39], checked 2026-10-16.

---

## 3. Docker environment variables, auth, health check, memory

### Environment variable naming (verified in the entrypoint [S16] and the docs [S40], checked 2026-10-16)

Rule: prefix `NEO4J_`, replace each `.` with `_`, and write each `_` that is part of the setting name as `__`. Settings written this way override both the image defaults and any values in a mounted `/conf/neo4j.conf`. Source: https://neo4j.com/docs/operations-manual/current/docker/configuration/ [S40].

| Setting | Environment variable |
|---|---|
| `server.memory.heap.initial_size` | `NEO4J_server_memory_heap_initial__size` |
| `server.memory.heap.max_size` | `NEO4J_server_memory_heap_max__size` |
| `server.memory.pagecache.size` | `NEO4J_server_memory_pagecache_size` |
| `dbms.memory.transaction.total.max` | `NEO4J_dbms_memory_transaction_total_max` |
| `db.memory.transaction.max` | `NEO4J_db_memory_transaction_max` |
| `server.jvm.additional` | `NEO4J_server_jvm_additional` (one variable holding all options; from Neo4j 5.6 these are appended to, not replacing, the defaults) |
| `dbms.security.procedures.unrestricted` | `NEO4J_dbms_security_procedures_unrestricted` |
| `dbms.security.procedures.allowlist` | `NEO4J_dbms_security_procedures_allowlist` |
| `db.query.default_language` | `NEO4J_db_query_default__language` |
| `server.directories.import` | `NEO4J_server_directories_import` (image default `/import`) |
| `dbms.security.auth_minimum_password_length` | `NEO4J_dbms_security_auth__minimum__password__length` |
| `apoc.import.file.enabled` | `NEO4J_apoc_import_file_enabled` |

The memory variable names above match the Operations Manual's Docker settings reference, which also lists `NEO4J_server_memory_pagecache_async` (introduced 2026.04). Source: neo4j/docs-operations `docker/ref-settings.adoc` [S41], checked 2026-10-16. The entrypoint still accepts the legacy `NEO4J_dbms_memory_pagecache_size` and maps it to the `server.*` name [S16].

Image defaults (checked 2026-10-16): the entrypoint writes `server.memory.pagecache.size=512M` and `server.default_listen_address=0.0.0.0` unless already set [S16]; the docs describe the Docker defaults as "NEO4J_server_memory_pagecache_size=512M and NEO4J_server_memory_heap_max__size=512M ... to allow multiple containers to be run on the same server" [S40]. Also set by the image: `server.directories.plugins=/plugins`, `server.directories.import=/import`, `server.directories.logs=/logs`, `server.directories.licenses=/licenses` [S16].

### NEO4J_AUTH

Verified in `set_initial_password` in the entrypoint [S16] and in [S14], checked 2026-10-16:

- Format `NEO4J_AUTH=neo4j/<password>`; the username must be `neo4j` (anything else exits with "Invalid admin username, it must be neo4j"); the password cannot be `neo4j`; minimum length 8 by default (the entrypoint prints a warning and the `neo4j-admin dbms set-initial-password` step can then fail, in which case the container does not start; override with `dbms.security.auth_minimum_password_length`).
- `NEO4J_AUTH=neo4j/<password>/true` forces a password change at first login (`--require-password-change`).
- `NEO4J_AUTH=none` disables authentication (`dbms.security.auth_enabled=false`). Do not ship this in the project compose file.
- `NEO4J_AUTH_PATH=/run/secrets/...` (or `NEO4J_AUTH_FILE` in the docs' compose example) reads the same `neo4j/<password>` string from a file, which is the Docker secrets route.
- `NEO4J_AUTH` only sets the initial password; if `/data` already contains a database it has no effect and the existing credentials apply [S14].

### Licence acceptance

- Not required for Community Edition, APOC Core or GDS Community. `NEO4J_ACCEPT_LICENSE_AGREEMENT=yes` is required only by the `-enterprise` image (Neo4j's own CI also uses the value `eval` for the evaluation licence). Source: [S14] and neo4j-graphrag-python `.github/workflows/pr-e2e-tests.yaml` [S42], checked 2026-10-16.

### Health check

The official image defines no HEALTHCHECK and the Operations Manual's compose example has none (https://neo4j.com/docs/operations-manual/current/docker/docker-compose-standalone/ [S43], checked 2026-10-16). Two working options:

Option A (Bolt-level, proves the database answers queries). This is exactly what Neo4j's own neo4j-graphrag-python e2e compose file uses with `docker compose up --wait` (tests/e2e/docker-compose.yml, commit 029ebd9, 15 October 2026 [S42], checked 2026-10-16):

```yaml
healthcheck:
  test: ["CMD-SHELL", "cypher-shell -u neo4j -p password 'RETURN 1' || exit 1"]
  interval: 5s
  timeout: 5s
  retries: 30
  start_period: 20s
```

Parameterised variant for a password supplied through `NEO4J_AUTH` (my derivation, uses POSIX `${var#pattern}` inside the container shell; `$$` is the compose escape; not executed during this research, mark as to-be-tested in CI):

```yaml
healthcheck:
  test: ["CMD-SHELL", "cypher-shell -u neo4j -p \"$${NEO4J_AUTH#*/}\" 'RETURN 1' || exit 1"]
  interval: 5s
  timeout: 10s
  retries: 30
  start_period: 30s
```

Option B (HTTP, no credentials, lighter). Use `wget`, not `curl`, because curl is not present in the image [S16]:

```yaml
healthcheck:
  test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:7474 || exit 1"]
  interval: 5s
  timeout: 5s
  retries: 30
  start_period: 20s
```

Readiness signals used by Neo4j's own tooling, for reference (checked 2026-10-16): Testcontainers Python waits for the log line "Remote interface available at" and then calls `driver.verify_connectivity()` [S44]; the docker-neo4j test-suite waits for HTTP 200 on port 7687 for Community and on `/db/<name>/cluster/available` (port 7474, basic auth) for Enterprise [S16]; neo4j-graphrag's GitHub Actions job polls `curl -s --fail http://localhost:7474` [S42]. Option A is the strictest and the one to use for `depends_on: condition: service_healthy`.

### Memory sizing

Guidance from the Operations Manual (https://neo4j.com/docs/operations-manual/current/performance/memory-configuration/ [S45], checked 2026-10-16): set heap initial and max to the same value; always set heap and page cache explicitly ("Otherwise, Neo4j computes heuristic values at startup"); page cache should cover data plus native indexes times about 1.2; leave memory for the OS; `dbms.memory.transaction.total.max` defaults to 70 percent of the heap (configuration reference [S46], checked 2026-10-16). The sizing tool `neo4j-admin server memory-recommendation --memory=16g --docker` prints `NEO4J_server_memory_heap_initial__size='5g'`, `NEO4J_server_memory_heap_max__size='5g'`, `NEO4J_server_memory_pagecache_size='7g'` and `NEO4J_server_jvm_additional='-XX:+ExitOnOutOfMemoryError'` for a dedicated 16 GB host. Source: neo4j/docs-operations `docker/operations.adoc` (served at https://neo4j.com/docs/operations-manual/current/docker/operations/) [S47], checked 2026-10-16.

Those numbers assume Neo4j owns the machine. On a developer laptop the container shares RAM with the OS, an IDE, a browser, the Python API, the Vite dev server and (on macOS or Windows) the Docker Desktop VM, so the recommendation below is my sizing, derived from the rules above and from the dataset size (500k nodes and 2M relationships is a store of a few hundred MB, so a 1 to 2 GB page cache holds it entirely; GDS projections of that size need a few hundred MB of heap). These values are recommendations, not Neo4j-published numbers:

| Laptop RAM | heap initial = max | page cache | transaction cap (`dbms.memory.transaction.total.max`) | Expected container RSS |
|---|---|---|---|---|
| 16 GB | 2G | 2G | 1G (leave default 70 percent otherwise) | about 5 GB including JVM overhead |
| 8 GB | 1G | 512M (image default) | 512M | about 2 GB; run the 10k-node "small dataset" mode and lower GDS `concurrency` to 2 |

Always add `NEO4J_server_jvm_additional=-XX:+ExitOnOutOfMemoryError` so a dead container restarts instead of limping (the memory-recommendation tool itself prints this line [S47]). On macOS and Windows, check the Docker Desktop resource limit before blaming Neo4j; the VM default is a fraction of host RAM (exact default: UNVERIFIED, not checked against Docker documentation in this research).

### Example compose service (assembled from the verified pieces above)

```yaml
services:
  neo4j:
    image: neo4j:5.26.32-community
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:?set NEO4J_PASSWORD in .env}
      NEO4J_PLUGINS: '["apoc","graph-data-science"]'
      NEO4J_server_memory_heap_initial__size: 2G
      NEO4J_server_memory_heap_max__size: 2G
      NEO4J_server_memory_pagecache_size: 2G
      NEO4J_server_jvm_additional: -XX:+ExitOnOutOfMemoryError
      NEO4J_apoc_import_file_enabled: "true"
      NEO4J_apoc_import_file_use__neo4j__config: "true"
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - ./data/import:/import:ro
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p \"$${NEO4J_AUTH#*/}\" 'RETURN 1' || exit 1"]
      interval: 5s
      timeout: 10s
      retries: 30
      start_period: 30s
volumes:
  neo4j_data:
  neo4j_logs:
```

`NEO4J_PLUGINS` adds `dbms.security.procedures.unrestricted=apoc.*,gds.*` itself; set `NEO4J_dbms_security_procedures_unrestricted` explicitly only if you also mount a `/conf` directory, because files in `/conf` replace the image's neo4j.conf entirely [S40].

---

## 4. Cypher 25 versus Cypher 5

- Cypher 25 was introduced with Neo4j 2025.06: "Cypher 25 is introduced alongside Neo4j 2025.06." From that release, Cypher 5 is frozen ("Neo4j will use Cypher 5 as it existed at the time of the Neo4j 2025.06 release") and "Any new Cypher features introduced in Neo4j 2025.06 or later will be exclusively added to Cypher 25." Source: https://neo4j.com/docs/cypher-manual/25/queries/select-version/ [S48] and the Cypher 25 deprecations page [S49], checked 2026-10-16.
- Consequence for 5.26 LTS: Cypher 25 "can only be used on Neo4j 2025.06+ databases" [S49]; Neo4j 5.26 has Cypher 5 only. (Direct inference from the quoted sentence; the docs do not state the 5.26 case explicitly.)
- Selecting the language:
  - Per query: prefix with `CYPHER 25` or `CYPHER 5` (combinable with other options, e.g. `CYPHER 5 runtime=slotted`). Source: [S48].
  - Per DBMS: the setting is `db.query.default_language` (valid values `CYPHER_5`, `CYPHER_25`, default `CYPHER_5`). Note the exact name; it is not `db.query_language`. Changing it affects only databases created afterwards. Source: neo4j/docs-operations `configuration/configuration-settings.adoc` and `configuration/cypher-version-configuration.adoc` (served at https://neo4j.com/docs/operations-manual/current/configuration/cypher-version-configuration/) [S50], checked 2026-10-16. Docker form: `NEO4J_db_query_default__language=CYPHER_25`.
  - Per database: `CREATE DATABASE x SET DEFAULT LANGUAGE CYPHER 25` or `ALTER DATABASE x SET DEFAULT LANGUAGE CYPHER 25` [S50]. In Community Edition there is only the one user database (`neo4j`), so the DBMS setting is the practical knob; whether `ALTER DATABASE neo4j SET DEFAULT LANGUAGE` is accepted in Community: UNVERIFIED (not tested).
  - Important default change: "Starting from Neo4j 2026.02, the distributed neo4j.conf explicitly sets db.query.default_language=CYPHER_25. As a result, new deployments using the provided configuration file default to Cypher 25 for newly created databases." Source: [S50] and `changes-2025-2026.adoc` [S51], checked 2026-10-16. The Docker images use the distributed neo4j.conf, so a fresh `neo4j:2026.02+` container runs Cypher 25 by default, while a fresh 2025.06 to 2026.01 container runs Cypher 5 by default.
- What Community users should default to: on `neo4j:5.26.32-community` there is no choice, write Cypher 5. Write it in the forward-compatible subset (below) so that the same loader and detection queries run unchanged under Cypher 25 after an upgrade. If the project ever moves to a 2026.x image, set `NEO4J_db_query_default__language` explicitly in compose and prefix queries in the copilot with `CYPHER 25` so behaviour does not depend on which image created the database.
- Syntax differences relevant to loading and pattern queries (all checked 2026-10-16 against the Cypher 25 manual source, neo4j/docs-cypher `deprecations-additions-removals-compatibility.adoc` at commit 332ce05 [S49], and the Cypher 5 manual's version of the same page on the `cypher-5` branch [S52]):
  1. Quantified path patterns exist in both: introduced in Neo4j 5.9 ("Introduction of quantified path patterns") and the `SHORTEST k` / `ALL SHORTEST` / `ANY` keywords in 5.21 [S52]. Cypher 25 adds `REPEATABLE ELEMENTS` and `DIFFERENT RELATIONSHIPS` path modes (2025.06) and `ACYCLIC` (2026.03, combinable with SHORTEST from 2026.05) [S49]. The payment-cycle and ownership-chain queries in the plan can be written with QPP on 5.26, e.g. `MATCH p = (a:Account)((:Account)-[:PAID]->(:Account)){3,6}(a)`.
  2. CALL subquery variable scope: since 5.23 "Using the WITH clause to import variables to CALL subqueries is deprecated, and replaced with a variable scope clause" and naked subqueries without a scope clause are deprecated [S52]. Cypher 25 still accepts the importing `WITH` but marks it deprecated [S53]. Use `CALL (row) { ... }` everywhere; it works on 5.26 and is the Cypher 25 form.
  3. Batched writes: `USING PERIODIC COMMIT` was removed in Neo4j 5.0; the replacement is `CALL { ... } IN TRANSACTIONS [OF n ROWS]`, which only runs in implicit (auto-commit) transactions, defaults to 1000 rows per batch, and since 5.21 supports `IN [n] CONCURRENT TRANSACTIONS` (so this is available in Cypher 5 on 5.26). `ON ERROR RETRY` was introduced in 2025.03 and `DISJOINT BY` in 2026.06 (Cypher 25 only). Source: https://neo4j.com/docs/cypher-manual/5/subqueries/subqueries-in-transactions/ [S54] and the Cypher 25 page [S55], checked 2026-10-16.
  4. Removed in Cypher 25 (available in Cypher 5): referring to another entity's property inside the same `MERGE` (`MERGE (a {foo:1})-[:T]->(b {foo:a.foo})` is an error, split it into two MERGEs); using a node or relationship as the right-hand side of `SET n = r` or `SET n += r` (use `SET n = properties(r)`); the `indexProvider` option in `CREATE INDEX` / `CREATE CONSTRAINT ... OPTIONS`; `$` and several Unicode characters in unescaped identifiers; the procedures `db.create.setVectorProperty()` and `db.index.vector.createNodeIndex()` (use `CREATE VECTOR INDEX`). Source: [S49] section "Neo4j 2025.06 / Removals".
  5. Deprecated but still present in both: `id()` is marked deprecated in favour of `elementId()` in both the Cypher 5 and Cypher 25 function references (source: `functions/scalar.adoc` on both branches of neo4j/docs-cypher [S53]); `shortestPath()` / `allShortestPaths()` without a variable-length relationship were deprecated in 5.0 and `SHORTEST` "functionally replaces and extends" them [S52]. Use `elementId()` in API payloads and `SHORTEST 1` in new queries.
  6. Search-index access is moving: in Cypher 25 the `SEARCH` clause is "the preferred way" to query vector indexes (2026.01) and full-text indexes (2026.09); `db.index.vector.queryNodes()` is deprecated in Cypher 25 since 2026.04 and `db.index.fulltext.queryNodes()` is deprecated from 2026.10. The procedures remain the only option in Cypher 5 and on 5.26. Source: neo4j/docs-cypher `indexes/syntax.adoc` and [S49], checked 2026-10-16.
  7. New in Cypher 25 that the team will not have on 5.26 (so do not copy from recent blog posts): `FOR` clause (2026.04), `LET`, `FILTER`, `WHEN ... ELSE`, `NEXT` (2025.06), map comprehension and string.* / coll.* function families (2025.11 to 2026.09), `IS [NOT] LABELED`, dynamic labels in label expressions (2025.07), `VECTOR` value type (2025.10). Source: [S49].

---

## 5. Constraints and indexes in Community Edition

Edition facts (Operations Manual edition table [S11], checked 2026-10-16): Community supports property uniqueness constraints (node and relationship, single and composite), range (label and property) indexes, composite indexes, token lookup indexes, text indexes, point indexes, full-text indexes and vector indexes. Property existence constraints, property type constraints and node or relationship key constraints are Enterprise only; the Cypher manual labels those three sections `label:enterprise-edition` (neo4j/docs-cypher `schema/constraints/index.adoc` [S56], checked 2026-10-16). In Community, enforce "property must exist" in the Python loader and in tests, not in the database.

Syntax (Cypher 25 manual source, `schema/syntax.adoc`, `schema/constraints/create-constraints.adoc`, `indexes/syntax.adoc` [S56, S57], checked 2026-10-16; identical in Cypher 5 for everything below except where noted):

```cypher
// Uniqueness constraint (Community OK). The NODE keyword is optional.
CREATE CONSTRAINT company_number IF NOT EXISTS
FOR (c:Company) REQUIRE c.companyNumber IS UNIQUE;

// Composite uniqueness (Community OK)
CREATE CONSTRAINT address_key IF NOT EXISTS
FOR (a:Address) REQUIRE (a.normalised, a.country) IS UNIQUE;

// Relationship property uniqueness (Community OK)
CREATE CONSTRAINT payment_id IF NOT EXISTS
FOR ()-[p:PAID]-() REQUIRE p.paymentId IS UNIQUE;

// Enterprise only, will fail on Community:
//   ... REQUIRE c.name IS NOT NULL            (existence)
//   ... REQUIRE c.name IS :: STRING            (type)
//   ... REQUIRE (c.a, c.b) IS NODE KEY         (key)

// Range index (RANGE keyword optional, no OPTIONS supported)
CREATE INDEX person_name IF NOT EXISTS
FOR (p:Person) ON (p.name);
CREATE INDEX paid_at IF NOT EXISTS
FOR ()-[r:PAID]-() ON (r.timestamp);

// Full-text index over several labels and properties
// (list analyzer names with CALL db.index.fulltext.listAvailableAnalyzers())
CREATE FULLTEXT INDEX entity_names IF NOT EXISTS
FOR (n:Person|Company) ON EACH [n.name, n.aliases]
OPTIONS { indexConfig: { `fulltext.analyzer`: 'standard-no-stop-words' } };

// Vector index (give dimensions and similarity function)
CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
FOR (n:Person|Company) ON (n.embedding)
OPTIONS { indexConfig: {
  `vector.dimensions`: 768,
  `vector.similarity_function`: 'cosine' } };

SHOW CONSTRAINTS;
SHOW INDEXES;
SHOW VECTOR INDEXES YIELD name, state, populationPercent;
SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties WHERE type = 'UNIQUENESS';
```

Notes:

- `FOR (n:Person|Company)` on a vector index (multiple labels) and the optional `WITH [n.extra, ...]` filter-property clause are Neo4j 2026.01+ and Cypher 25 only; on 5.26 create one vector index per label with a single property. Source: `indexes/syntax.adoc` ("As of Neo4j 2026.01, vector indexes support multiple labels, multiple relationship types, and additional properties for filtering") [S57], checked 2026-10-16.
- Querying on 5.26: `CALL db.index.fulltext.queryNodes('entity_names', 'acme~', {limit: 20}) YIELD node, score` and `CALL db.index.vector.queryNodes('entity_embedding', 10, $vector) YIELD node, score`. On Cypher 25 the `SEARCH n IN (FULLTEXT INDEX ... FOR ... LIMIT ...)` and `SEARCH n IN (VECTOR INDEX ... FOR $vector LIMIT ...)` clauses are preferred (see section 4). Source: [S57].
- A uniqueness constraint creates its backing range index, so do not also create a plain index on the same property. `SHOW INDEXES` lists it with the constraint's name (`ownedIndex`). Source: [S56].
- `IF NOT EXISTS` makes the DDL idempotent, which is what the loader's "ensure schema" step should use. Source: `indexes/syntax.adoc` ("The CREATE ... INDEX ... command is optionally idempotent") [S57].

---

## 6. Bulk loading in Community Edition

### Options

1. `LOAD CSV` (online, Cypher). Reads `file:///` paths relative to `server.directories.import` (`/import` in the image) when `dbms.security.allow_csv_import_from_file_urls` is true (default), or `http(s)://` URLs; local files may be gzip or zip compressed (one CSV per zip; compressed files cannot come from remote URLs). All values arrive as STRING and must be cast (`toInteger`, `date`, ...). "LOAD CSV may run into memory issues with files containing a significant number of rows (approaching hundreds of thousands or millions). For large files, it's recommended to split the import process in several lighter transactions through the clause CALL {...} IN TRANSACTIONS." Neo4j positions LOAD CSV for "small- to medium-sized datasets (up to 10 million records)". Sources: neo4j/docs-cypher `clauses/load-csv.adoc` (served at https://neo4j.com/docs/cypher-manual/25/clauses/load-csv/) [S58] and https://neo4j.com/docs/getting-started/data-import/ [S59], checked 2026-10-16. Pattern:

   ```cypher
   LOAD CSV WITH HEADERS FROM 'file:///companies.csv' AS row
   CALL (row) {
     MERGE (c:Company {companyNumber: row.company_number})
     SET c.name = row.name, c.incorporated = date(row.incorporated)
   } IN TRANSACTIONS OF 10000 ROWS
   ```
   In Neo4j Browser prefix this with `:auto`. From the Python driver it must be sent as an auto-commit query (`driver.execute_query` is fine; a managed transaction function is not, because CALL IN TRANSACTIONS "is only allowed in implicit transactions" [S54]). `IN 4 CONCURRENT TRANSACTIONS OF 10000 ROWS` is available on 5.26 (introduced 5.21) [S54]; use it only when batches touch disjoint parts of the graph (node loads yes, relationship loads carefully) because concurrent batches can deadlock [S39].

2. `neo4j-admin database import full` (offline, fastest). "writes CSV data into Neo4j's native file format as fast as possible", for a "non-existent or empty database"; importing into an existing database requires `--overwrite-destination`; CSV must be clean (no duplicate node IDs, relationship endpoints must exist) because fault handling is "not optimized". Index and constraint creation during import is Block format and therefore Enterprise only; in Community, create constraints afterwards with Cypher. Source: neo4j/docs-operations `import/index.adoc` and `import/full-import.adoc` (served at https://neo4j.com/docs/operations-manual/current/import/) [S60], checked 2026-10-16. In Docker the documented way is to run the command in a container that mounts the same `/data` and `/import` volumes, before the server container starts (or `docker exec` into a stopped-database server, which in Community means the server must not be running since the only database is `neo4j`): https://neo4j.com/docs/operations-manual/current/docker/operations/ [S47], checked 2026-10-16. A compose "init" service with `depends_on: condition: service_completed_successfully` on the neo4j service implements this.

3. `neo4j-admin database import incremental`: Enterprise only (page role `enterprise-edition` in `import/incremental-import.adoc`, and the edition table marks "Incremental import" as Enterprise). Source: [S60] and [S11], checked 2026-10-16. Not available to this project.

4. Python driver with `UNWIND $rows AS row MERGE ...` in batches. The driver manual's performance page: "Batch queries when creating a lot of records using the WITH and UNWIND Cypher clauses" and its example sends 10,000 values in one query; always use parameters. Source: https://neo4j.com/docs/python-manual/current/performance/ [S61], checked 2026-10-16. Neo4j's long-standing rule of thumb for transaction size is "Something between 10,000 and 100,000 updates per transaction are a good target" (Michael Hunger, 2016 import post). Source: https://neo4j.com/blog/cypher-and-gql/bulk-data-import-neo4j-3-0/ [S62], checked 2026-10-16. Pattern:

   ```python
   driver.execute_query(
       """
       UNWIND $rows AS row
       MERGE (c:Company {companyNumber: row.companyNumber})
       SET c += row.props
       """,
       rows=batch, database_="neo4j",
   )
   ```
   with batches of 5,000 to 10,000 rows per call; for relationships MATCH both endpoints by their constrained key, then MERGE the relationship.

5. `apoc.periodic.iterate(cypherIterate, cypherAction, {batchSize: 10000, parallel: false, retries: 3})`: in APOC Core, works on 5.26, deprecated under Cypher 25 from 2026.04 (section 2). Source: [S37], checked 2026-10-16. Prefer `CALL { } IN TRANSACTIONS` for new code so nothing has to be rewritten later.

### Throughput expectations for 500k nodes and 2M relationships on a laptop

Primary numbers are scarce. The only Neo4j-published figure found is from 2016: neo4j-admin import loaded "30 million nodes, 78 million relationships and 280 million properties ... in three minutes and eight seconds" on an unspecified multi-core server (about 160k nodes/s and 415k relationships/s, my division). Source: [S62], checked 2026-10-16. Everything below is therefore an estimate (UNVERIFIED as a benchmark) that the project should replace with its own measured numbers in CI during sprint 0:

| Method | Expected on a 2023-era laptop, SSD, settings from section 3 | Notes |
|---|---|---|
| `neo4j-admin database import full` | 500k nodes + 2M rels in well under one minute, likely 10 to 40 s | Offline only, clean CSV, constraints created afterwards |
| `LOAD CSV ... CALL IN TRANSACTIONS OF 10000 ROWS` with MERGE on constrained keys | nodes about 5k to 20k rows/s (30 to 100 s); relationships about 2k to 8k rows/s (4 to 15 min) | Dominated by index lookups on both endpoints; CREATE is faster than MERGE |
| Python `UNWIND` batches of 10k over Bolt | similar to LOAD CSV, slightly slower per row because of client serialisation; 5 to 20 minutes total | Can overlap CPU work (entity resolution) with loading; supports retries |
| `apoc.periodic.iterate` | same ballpark as CALL IN TRANSACTIONS | Deprecated under Cypher 25 |

### Recommended approach for this project

Use the Python loader with `UNWIND` batches (option 4) as the primary path: it is online, Community-safe, idempotent through MERGE on uniqueness-constrained keys, resumable, and it keeps entity resolution and loading in one Python process. Create all uniqueness constraints (section 5) before loading anything; load nodes first and relationships second; keep batches at 5k to 10k rows; use `execute_query` with the `database_` argument. Offer `neo4j-admin database import full` as an optional fast path for the full dataset in a compose init service once the CSV format is stable, because it fits comfortably in the "under 10 minutes" budget even on an 8 GB laptop. Reserve `LOAD CSV` for notebooks and the day-3 onboarding exercise.

---

## 7. Neo4j Python driver

- Latest release on PyPI: `neo4j` 6.4.1, uploaded 15 October 2026. Requires Python >= 3.10; classifiers list 3.10, 3.11, 3.12, 3.13, 3.14 and 3.15. Licence expression "Apache-2.0 AND Python-2.0". Source: PyPI JSON API https://pypi.org/pypi/neo4j/json [S63], checked 2026-10-16.
- 6.x history (first upload dates from PyPI [S63], checked 2026-10-16): 6.0.0 on 30 September 2025, 6.0.3 on 6 November 2025, 6.1.0 on 12 January 2026 (adds Python 3.14), 6.2.0 on 4 May 2026, 6.3.0 on 28 August 2026, 6.3.1 on 15 September 2026, 6.4.0 on 5 October 2026 (adds Python 3.15), 6.4.1 on 15 October 2026. The 5.x line is still patched (5.28.8 on 15 October 2026).
- The old package name `neo4j-driver` is deprecated and "will receive no further updates starting with 6.0.0"; install `neo4j`. Source: README on PyPI [S64], checked 2026-10-16.
- What changed in 6.0 (from CHANGELOG.md in neo4j/neo4j-python-driver, commit 9755761, 15 October 2026 [S65], checked 2026-10-16): Python 3.7 to 3.9 dropped; `setup.py` removed (pyproject only); deprecated modules removed (`neo4j.conf`, `neo4j.data`, `neo4j.meta`, `neo4j.packstream`, `neo4j.routing`, `neo4j.work`, ...); `session.read_transaction` / `write_transaction` removed in favour of `execute_read` / `execute_write`; `neo4j.Bookmark` and `session.last_bookmark()` removed in favour of `neo4j.Bookmarks` and `last_bookmarks()`; the `trust` driver option removed in favour of `trusted_certificates`; `Neo4jError.is_retriable` removed in favour of `is_retryable`; `ServerInfo.connection_id` and `api.Version` removed; error classes reshuffled so client-side failures raise `DriverError` subclasses (`ConfigurationError`, `TransactionError`, new `ConnectionAcquisitionTimeoutError`) rather than `Neo4jError`; `Neo4jError.message` and `.code` are always `str`; notifications APIs deprecated in favour of GQL status objects; `PreviewWarning` moves to `neo4j.warnings`. 6.1 to 6.4: no breaking changes except that 6.4 deprecates URIs that contain a path or fragment.
- Server compatibility: "The latest 6.x driver supports connection to Neo4j instances version 4.4, 5.x, and 2025.x" (the page predates 2026.x but Neo4j's own neo4j-graphrag CI runs driver 6 against `neo4j:latest`, i.e. 2026.x [S42]). Source: https://neo4j.com/docs/python-manual/current/install/ [S66], checked 2026-10-16.
- Recommended pattern: `driver.execute_query()`; it wraps the query in a managed transaction with automatic retry of transient failures, returns `(records, summary, keys)` (an `EagerResult`), always pass `database_="neo4j"` to save a round trip, use `routing_=RoutingControl.READ` for reads (irrelevant on single-instance Community but harmless), `result_transformer_` for DataFrames. Use `session.execute_write(fn)` / `execute_read(fn)` when several queries must share one transaction or when results must be streamed; transaction functions must be idempotent because they can be retried. Sessions are not thread-safe. Source: https://neo4j.com/docs/python-manual/current/query-simple/ [S67] and https://neo4j.com/docs/python-manual/current/transactions/ [S68], checked 2026-10-16.

  ```python
  from neo4j import GraphDatabase, RoutingControl

  with GraphDatabase.driver(uri, auth=(user, password)) as driver:
      driver.verify_connectivity()
      records, summary, keys = driver.execute_query(
          "MATCH (c:Company {companyNumber: $n}) RETURN c.name AS name",
          n="01234567", database_="neo4j", routing_=RoutingControl.READ,
      )
  ```
- asyncio: `from neo4j import AsyncGraphDatabase`; `async with AsyncGraphDatabase.driver(...) as driver: await driver.execute_query(...)`; the same API shape with `await`. The manual's only caveats are that the async driver had a known slowdown on Python 3.8 (irrelevant now) and that multithreading is the alternative concurrency model. Source: https://neo4j.com/docs/python-manual/current/concurrency/ [S69], checked 2026-10-16. The async driver fits a FastAPI backend; create one `AsyncDriver` per process at startup and close it on shutdown. Optional `neo4j-rust-ext` speeds up packing and unpacking (same version numbers as the driver) [S64].

---

## 8. neo4j-graphrag Python package

- Latest: `neo4j-graphrag` 1.22.0, uploaded 1 October 2026 (1.21.0 on 23 September 2026, 1.19.0 on 26 August 2026). Requires Python >= 3.10 and < 3.15; core dependencies include `neo4j>=6.3.1,<7.0.0`, `pydantic>=2.6.3,<3`, `numpy`, `scipy`, `fsspec`, `pypdf`, `json-repair`, `tenacity`. Optional extras include `ollama` (`ollama>=0.4.4,<0.5.0`), `openai`, `anthropic`, `mistralai`, `cohere`, `google-genai`, `sentence-transformers`, `litellm`, `qdrant`, `weaviate`, `pinecone`. Licence Apache 2.0. Source: PyPI JSON API https://pypi.org/pypi/neo4j-graphrag/json [S70], checked 2026-10-16.
- Text2CypherRetriever (`neo4j_graphrag.retrievers.Text2CypherRetriever`) constructor: `driver: neo4j.Driver`, `llm: LLMInterface`, `neo4j_schema: Optional[str]`, `examples: Optional[list[str]]`, `result_formatter`, `custom_prompt: Optional[str]`, `neo4j_database: Optional[str]`. If `neo4j_schema` is not given it calls `get_schema(driver)` itself and raises `SchemaFetchError` on failure; `search(query_text, prompt_params)` can override `schema` and `examples` per call. Source: `src/neo4j_graphrag/retrievers/text2cypher.py` at commit 029ebd9 (15 October 2026) [S71], checked 2026-10-16.
- Safety feature worth citing in the project docs: since 1.16.0 "Text2CypherRetriever now runs EXPLAIN on the LLM-generated Cypher and refuses to execute anything that is not read-only, raising Text2CypherRetrievalError" to block prompt-injected writes such as `DETACH DELETE`. Source: CHANGELOG.md in the same repo [S71], checked 2026-10-16.
- Custom or local LLM: yes. The LLM abstraction is `neo4j_graphrag.llm.LLMInterface` (v1, string input) and `LLMInterfaceV2` (message list input, structured output); since 1.15.0 the recommended base class is `LLMBase`, which combines both, and the user guide's "Using a Custom Model" section shows a `MyOllamaLLM(LLMBase)` example. A ready-made `OllamaLLM(model_name=..., model_params={...}, host=...)` exists (install the `ollama` extra); it uses `ollama.Client` and `ollama.AsyncClient`, supports tool calling (since 1.10.1) and defaults to `127.0.0.1:11434`. Source: `src/neo4j_graphrag/llm/ollama_llm.py`, `docs/source/user_guide_rag.rst`, `examples/customize/llms/ollama_llm.py` [S71], checked 2026-10-16. Any other provider (an OpenAI-compatible endpoint such as vLLM or LM Studio, or the Anthropic API) is either built in or a small `LLMBase` subclass.
- Schema helpers in `neo4j_graphrag.schema`: `get_schema(driver, is_enhanced=False, database=None, timeout=None, sanitize=False, sample=1000) -> str` returns the text block ("Node properties: ... Relationship properties: ... The relationships: ...") that Text2Cypher puts in the prompt; `get_structured_schema(...) -> dict` returns `node_props`, `rel_props`, `relationships` and `metadata` (constraints and indexes); `format_schema(schema, is_enhanced)` renders the dict. Both depend on APOC: "The internal structure of the returned dict depends on the apoc.meta.data and apoc.schema.nodes procedures", and the `sample` argument controls `apoc.meta.data` sampling (-1 disables sampling). So APOC Core must be installed in the container (it is, via `NEO4J_PLUGINS`). Source: `src/neo4j_graphrag/schema.py` [S71], checked 2026-10-16.
- Compatibility with 5.26: Neo4j's own CI for the package runs the e2e suite against both `neo4j:5-enterprise` and `neo4j:latest`, with the Cypher 25 `SEARCH`-clause tests excluded on 5.x ("not search_clause"). The package's SEARCH-based features need a 2026.02.2+ server; Text2Cypher, vector and hybrid retrievers run on 5.26. Source: `.github/workflows/pr-e2e-tests.yaml` and README [S42], checked 2026-10-16.
- Python 3.14 note: the `nlp` extra (spaCy) is "not supported on Python 3.14" (README) [S42]; irrelevant unless the project uses the KG-builder NLP components.

---

## 9. Testing: GitHub Actions and Testcontainers

### GitHub Actions

- There is no Neo4j-published "service container" example in the Neo4j documentation (searched neo4j.com docs and the developer blog on 2026-10-16; the only Neo4j-domain hits are community forum threads from 2020 and 2021). UNVERIFIED that none exists elsewhere on neo4j.com, but none was found.
- What Neo4j itself does: the neo4j-graphrag-python workflow starts Neo4j with `docker run -d --name neo4j -p 7687:7687 -p 7474:7474 -e NEO4J_AUTH=neo4j/password -e NEO4J_ACCEPT_LICENSE_AGREEMENT=eval -e NEO4J_PLUGINS='["apoc"]' neo4j:${{ matrix.neo4j-tag }}` and then polls `curl -s --fail http://localhost:7474` up to 30 times at 5 s intervals before running pytest. Source: `.github/workflows/pr-e2e-tests.yaml` at commit 029ebd9 [S42], checked 2026-10-16.
- A `services:` block equivalent, assembled from GitHub's documented service-container syntax (the `options` field passes `--health-cmd`, `--health-interval`, `--health-timeout`, `--health-retries` through to Docker, as in GitHub's Redis example) and the Neo4j image facts above. Source for the syntax: https://docs.github.com/en/actions/use-cases-and-examples/using-containerized-services/about-service-containers [S72] and https://docs.github.com/en/actions/use-cases-and-examples/using-containerized-services/creating-redis-service-containers [S73], checked 2026-10-16. This block is my composition, not an official Neo4j example:

  ```yaml
  jobs:
    test:
      runs-on: ubuntu-latest
      services:
        neo4j:
          image: neo4j:5.26.32-community
          env:
            NEO4J_AUTH: neo4j/testpassword
            NEO4J_PLUGINS: '["apoc","graph-data-science"]'
            NEO4J_server_memory_heap_initial__size: 1G
            NEO4J_server_memory_heap_max__size: 1G
            NEO4J_server_memory_pagecache_size: 512M
          ports:
            - 7687:7687
            - 7474:7474
          options: >-
            --health-cmd "cypher-shell -u neo4j -p testpassword 'RETURN 1'"
            --health-interval 10s
            --health-timeout 10s
            --health-retries 20
            --health-start-period 30s
      steps:
        - uses: actions/checkout@v7
        - uses: actions/setup-python@v7
          with: { python-version: "3.12" }
        - run: pip install -e ".[test]"
        - run: pytest tests/integration
          env:
            NEO4J_URI: bolt://localhost:7687
            NEO4J_USERNAME: neo4j
            NEO4J_PASSWORD: testpassword
  ```
  Because the job runs on the runner (not in a container), the service is reached at `localhost:7687`; inside a job container it would be `neo4j:7687` (the service label). GitHub waits for the health check before running steps. Note GitHub Actions does not let you mount volumes into a `services:` container from the checkout, so CSV fixtures for `LOAD CSV` must be served over HTTP or loaded through the driver; Testcontainers (below) avoids this limitation.

### Testcontainers for Python

- Package: `testcontainers` on PyPI, latest 4.15.0 (24 July 2026), requires Python >= 3.10, Apache-2.0. Install with the extra: `pip install "testcontainers[neo4j]" neo4j`; the `neo4j` extra pins `neo4j>=6`. Source: PyPI JSON API https://pypi.org/pypi/testcontainers/json [S74] and `pyproject.toml` in testcontainers/testcontainers-python (commit 6146aa1, 7 October 2026) [S75], checked 2026-10-16.
- Import path: `from testcontainers.community.neo4j import Neo4jContainer`. The old path `testcontainers.neo4j` still works in 4.15.0 but emits `DeprecationWarning: testcontainers.neo4j is deprecated, use testcontainers.community.neo4j instead`. Verified by inspecting the 4.15.0 wheel downloaded from PyPI (`testcontainers/neo4j.py` is a shim, the implementation is `testcontainers/community/neo4j/__init__.py`) [S76], checked 2026-10-16.
- Behaviour (same wheel [S76]): `Neo4jContainer(image="neo4j:latest", port=7687, password=None, username=None, **kwargs)`; the password defaults to `$NEO4J_PASSWORD` or `"password"`, the username to `$NEO4J_USER` or `"neo4j"`; it sets `NEO4J_AUTH=neo4j/<password>`, exposes 7687, waits for the log line "Remote interface available at" and then calls `driver.verify_connectivity()`; `get_connection_url()` returns `bolt://<host>:<mapped port>`; `get_driver(**kwargs)` returns a `neo4j.Driver`.
- Enabling plugins: there is no dedicated method; use the generic `with_env`. Volumes use `with_volume_mapping`. Example (my composition from the verified API):

  ```python
  from testcontainers.community.neo4j import Neo4jContainer

  def neo4j_container():
      return (
          Neo4jContainer(image="neo4j:5.26.32-community", password="testpassword")
          .with_env("NEO4J_PLUGINS", '["apoc","graph-data-science"]')
          .with_env("NEO4J_server_memory_heap_max__size", "1G")
          .with_env("NEO4J_server_memory_pagecache_size", "512M")
          .with_volume_mapping(str(FIXTURES_DIR), "/import", "ro")
      )

  with neo4j_container() as neo4j, neo4j.get_driver() as driver:
      driver.execute_query("RETURN gds.version() AS v", database_="neo4j")
  ```
  Pin the image in tests to the same tag as compose so CI and laptops run identical servers. The first `NEO4J_PLUGINS` start copies the bundled jars (no download) but still restarts nothing; expect roughly 15 to 40 s container start on a laptop (my estimate, UNVERIFIED).

---

## 10. Neo4j Browser and Bloom in Community

- Neo4j Browser remains bundled and served by the database's HTTP connector: open `http://localhost:7474/browser` (the web server hosts the `BROWSER` module on port 7474 by default; remove `BROWSER` from `dbms.http_enabled_modules` to turn it off). "Browser is included in both Community Edition and Enterprise Edition", and it is "the default developer interface for both Enterprise and Community editions of Neo4j". Source: https://neo4j.com/docs/browser-manual/current/deployment-modes/neo4j-server/ [S77] and https://neo4j.com/docs/browser-manual/current/ [S78], checked 2026-10-16. The Docker image docs still describe 7474 as "the Neo4j Browser web interface" [S14].
- Naming: the product is still called Neo4j Browser on self-managed servers; in AuraDB and Neo4j Desktop the same tool is offered as "Query" [S78]. Browser now uses calendar-style versions: 2026.09.0 bundles Browser 2026.09.18+0 [S6], 5.26.31 bundles 2026.09.21+0 [S20] and 5.26.32 bundles 2026.10.08+0 [S3], so the LTS image carries the current Browser. The Browser manual has a "current" and a "legacy" version selector; whether any server still ships the legacy Browser UI or offers a switch back: UNVERIFIED (the legacy manual is blocked to the fetch tool and the current manual does not say).
- Packaging change: from Neo4j 2026.02.3 "A new directory web is introduced in the Neo4j Community Edition. The web directory contains Neo4j Browser bundled as a .zip file", while Enterprise keeps Browser as a jar in lib. This is packaging only; the URL and port are unchanged. Source: neo4j/docs-operations `changes-2025-2026.adoc` [S51], checked 2026-10-16.
- Bloom: not available in Community. The edition table marks "Support for Neo4j Bloom" as Enterprise only [S11]; the Bloom installation guide requires "User access to a Neo4j Enterprise Edition database" for the client and "Admin access to a licensed Neo4j Enterprise Edition database" for the server, with the Docker plugin needing Enterprise 4.2.3+ and a licence file mounted at `/licenses/bloom.license`. Source: https://neo4j.com/docs/bloom-user-guide/current/bloom-installation/ [S79], checked 2026-10-16. The plan's fallback of "Neo4j Bloom screenshots for the pretty pictures" would need someone with Neo4j Desktop (Bloom client is enabled there) or an Enterprise evaluation; it cannot come from the project's Community stack. The free alternative is Browser's graph view, or the project's own Cytoscape.js explorer.

---

## Recommendations

1. Image: `neo4j:5.26.32-community`, pinned exactly in `compose.yaml`, the devcontainer, Testcontainers and CI. Review newer 5.26.x patches as explicit pull requests; do not float on `5.26-community`. Revisit the choice only after the 2026 LTS ships and GDS, APOC, the Python driver and neo4j-graphrag have confirmed support for it.
2. Plugins: `NEO4J_PLUGINS='["apoc","graph-data-science"]'`. On this image that yields APOC Core 5.26.32 and GDS 2.13.14 from the bundled jars, offline. Document the GDS Community 4-core concurrency cap and pass `concurrency: 4` in GDS calls.
3. Python: `neo4j>=6.4,<7`, `neo4j-graphrag>=1.22,<2` (needs `neo4j>=6.3.1`), `graphdatascience>=2.2,<3` if the GDS Python client is used (it supports GDS 2.13 and driver 5.26+), `testcontainers[neo4j]>=4.15`. Use `driver.execute_query(..., database_="neo4j")` everywhere; `AsyncGraphDatabase` in the API process.
4. Cypher: write Cypher 5 in the forward-compatible subset: `CALL (vars) { }`, `elementId()`, `:A&B` label expressions, quantified path patterns and `SHORTEST k`, `CALL { } IN TRANSACTIONS OF 10000 ROWS` for batching, no cross-entity property references inside one MERGE, no `SET n = otherEntity`, no `indexProvider` options. Keep `apoc.periodic.iterate` out of new code. Add `NEO4J_db_query_default__language` to compose the day the image moves to 2026.x.
5. Schema: uniqueness constraints only (Community); enforce existence and types in the Python loader and in the test fixtures. One range index per frequently filtered property, one full-text index for entity name search, one vector index per label if the copilot needs embeddings.
6. Loading: Python `UNWIND` batches of 5k to 10k through `execute_query`, nodes before relationships, constraints created first. Add an optional `neo4j-admin database import full` init service for the full dataset once the CSV format freezes. Measure throughput in CI in sprint 0 and replace the estimates in section 6 with real numbers.
7. Health and memory: cypher-shell health check with `start_period: 30s`; heap 2G/2G and page cache 2G on 16 GB laptops, 1G/1G and 512M on 8 GB laptops together with the 10k-node small dataset mode; `-XX:+ExitOnOutOfMemoryError` always.
8. Visuals: no Bloom. Use Browser at :7474 for teaching and the project's Cytoscape explorer for the demo.

---

## Sources

All checked on 16 October 2026.

- [S1] https://neo4j.com/blog/developer/neo4j-v5-lts-evolution/
- [S2] https://neo4j.com/release-notes/database/
- [S3] https://neo4j.com/release-notes/database/neo4j-5-26-32/
- [S4] https://neo4j.com/docs/upgrade-migration-guide/current/
- [S5] https://endoflife.date/neo4j (third-party tracker, used only for the per-line support windows and cross-checked against S2)
- [S6] https://neo4j.com/release-notes/database/neo4j-2026-09-0/
- [S7] https://github.com/neo4j/docs-operations (antora.yml, commit 8b6a119, cloned read-only)
- [S8] https://neo4j.com/docs/upgrade-migration-guide/current/version-2025-2026/upgrade/
- [S9] https://github.com/neo4j/graph-data-science (README.adoc and LICENSE.txt, commit 417d7ec, cloned read-only)
- [S10] https://hub.docker.com/v2/repositories/library/neo4j/tags?page_size=100&name=community
- [S11] https://raw.githubusercontent.com/neo4j/docs-operations/dev/modules/ROOT/pages/introduction.adoc (edition comparison table; rendered page https://neo4j.com/docs/operations-manual/current/introduction/)
- [S12] https://hub.docker.com/v2/repositories/library/neo4j/tags?page_size=100&name=5.26
- [S13] https://hub.docker.com/v2/repositories/library/neo4j/tags?page_size=100&name=2026 and ...&name=latest
- [S14] https://neo4j.com/docs/operations-manual/current/docker/introduction/
- [S15] https://github.com/docker-library/docs/blob/master/neo4j/README.md
- [S16] https://github.com/neo4j/docker-neo4j (docker-image-src/calver/coredb/{docker-entrypoint.sh,neo4j-plugins.json,Dockerfile-trixie,Dockerfile-ubi10}, docker-image-src/5/coredb/Dockerfile-trixie, src/test/java/com/neo4j/docker/utils/WaitStrategies.java, commit fd9e4ec, cloned read-only)
- [S17] https://neo4j.com/release-notes/gds/
- [S18] https://neo4j.com/release-notes/gds/graph-data-science-2026-09-0/
- [S19] https://neo4j.com/docs/graph-data-science/current/installation/supported-neo4j-versions/
- [S20] https://neo4j.com/release-notes/database/neo4j-5-26-31/
- [S21] https://neo4j.com/docs/operations-manual/current/configuration/plugins/ (read from docs-operations modules/ROOT/pages/configuration/plugins.adoc)
- [S22] https://neo4j.com/docs/graph-data-science/current/installation/neo4j-server/
- [S23] https://pypi.org/pypi/graphdatascience/json
- [S24] https://github.com/neo4j/graph-data-science-client (doc/modules/ROOT/pages/installation.adoc and migration-from-1x.adoc, commit 4457aa6, cloned read-only)
- [S25] https://neo4j.com/docs/graph-data-science/current/installation/installation-docker/
- [S26] https://neo4j.com/docs/operations-manual/current/docker/plugins/
- [S27] https://graphdatascience.ninja/versions.json
- [S28] https://neo4j.com/docs/graph-data-science/current/installation/
- [S29] https://neo4j.com/docs/graph-data-science/current/introduction/
- [S30] https://neo4j.com/docs/apoc/current/installation/
- [S31] https://neo4j.com/docs/apoc/current/
- [S32] https://neo4j.github.io/apoc/versions.json
- [S33] https://neo4j.com/docs/apoc/current/config/
- [S34] https://github.com/neo4j/apoc (LICENSE, commit 4288f52, cloned read-only)
- [S35] https://neo4j.com/docs/apoc/current/introduction/
- [S36] https://neo4j.com/docs/apoc/current/overview/apoc.periodic/
- [S37] https://neo4j.com/docs/apoc/current/overview/apoc.periodic/apoc.periodic.iterate/
- [S38] https://neo4j.com/docs/apoc/current/deprecations-and-additions/
- [S39] https://graphacademy.neo4j.com/blog/replace-apoc-periodic-iterate-with-call-in-transactions
- [S40] https://neo4j.com/docs/operations-manual/current/docker/configuration/
- [S41] https://neo4j.com/docs/operations-manual/current/docker/ref-settings/ (read from docs-operations modules/ROOT/pages/docker/ref-settings.adoc)
- [S42] https://github.com/neo4j/neo4j-graphrag-python (.github/workflows/pr-e2e-tests.yaml, tests/e2e/docker-compose.yml, tests/e2e/docker-compose.neo4j2026.yml, README.md, commit 029ebd9, cloned read-only)
- [S43] https://neo4j.com/docs/operations-manual/current/docker/docker-compose-standalone/
- [S44] https://github.com/testcontainers/testcontainers-python (src/testcontainers/community/neo4j/__init__.py, commit 6146aa1, cloned read-only)
- [S45] https://neo4j.com/docs/operations-manual/current/performance/memory-configuration/
- [S46] https://neo4j.com/docs/operations-manual/current/configuration/configuration-settings/
- [S47] https://neo4j.com/docs/operations-manual/current/docker/operations/ (read from docs-operations modules/ROOT/pages/docker/operations.adoc)
- [S48] https://neo4j.com/docs/cypher-manual/25/queries/select-version/
- [S49] https://neo4j.com/docs/cypher-manual/25/deprecations-additions-removals-compatibility/ (read from neo4j/docs-cypher dev branch, commit 332ce05)
- [S50] https://neo4j.com/docs/operations-manual/current/configuration/cypher-version-configuration/ (read from docs-operations modules/ROOT/pages/configuration/cypher-version-configuration.adoc and configuration-settings.adoc)
- [S51] https://neo4j.com/docs/operations-manual/current/changes-2025-2026/ (read from docs-operations modules/ROOT/pages/changes-2025-2026.adoc)
- [S52] https://neo4j.com/docs/cypher-manual/5/deprecations-additions-removals-compatibility/ (read from neo4j/docs-cypher branch cypher-5)
- [S53] https://github.com/neo4j/docs-cypher (modules/ROOT/pages/subqueries/call-subquery.adoc and functions/scalar.adoc on both dev and cypher-5 branches)
- [S54] https://neo4j.com/docs/cypher-manual/5/subqueries/subqueries-in-transactions/
- [S55] https://neo4j.com/docs/cypher-manual/25/subqueries/subqueries-in-transactions/
- [S56] https://neo4j.com/docs/cypher-manual/25/schema/constraints/ (read from neo4j/docs-cypher modules/ROOT/pages/schema/constraints/*.adoc and schema/syntax.adoc)
- [S57] https://neo4j.com/docs/cypher-manual/25/indexes/syntax/ (read from neo4j/docs-cypher modules/ROOT/pages/indexes/syntax.adoc)
- [S58] https://neo4j.com/docs/cypher-manual/25/clauses/load-csv/ (read from neo4j/docs-cypher modules/ROOT/pages/clauses/load-csv.adoc)
- [S59] https://neo4j.com/docs/getting-started/data-import/
- [S60] https://neo4j.com/docs/operations-manual/current/import/ (read from docs-operations modules/ROOT/pages/import/{index,full-import,incremental-import}.adoc)
- [S61] https://neo4j.com/docs/python-manual/current/performance/
- [S62] https://neo4j.com/blog/cypher-and-gql/bulk-data-import-neo4j-3-0/
- [S63] https://pypi.org/pypi/neo4j/json
- [S64] https://pypi.org/project/neo4j/
- [S65] https://github.com/neo4j/neo4j-python-driver (CHANGELOG.md and README.rst, commit 9755761, cloned read-only)
- [S66] https://neo4j.com/docs/python-manual/current/install/
- [S67] https://neo4j.com/docs/python-manual/current/query-simple/
- [S68] https://neo4j.com/docs/python-manual/current/transactions/
- [S69] https://neo4j.com/docs/python-manual/current/concurrency/
- [S70] https://pypi.org/pypi/neo4j-graphrag/json
- [S71] https://github.com/neo4j/neo4j-graphrag-python (src/neo4j_graphrag/retrievers/text2cypher.py, src/neo4j_graphrag/schema.py, src/neo4j_graphrag/llm/{base,ollama_llm}.py, docs/source/user_guide_rag.rst, examples/customize/llms/ollama_llm.py, CHANGELOG.md, commit 029ebd9)
- [S72] https://docs.github.com/en/actions/use-cases-and-examples/using-containerized-services/about-service-containers
- [S73] https://docs.github.com/en/actions/use-cases-and-examples/using-containerized-services/creating-redis-service-containers
- [S74] https://pypi.org/pypi/testcontainers/json
- [S75] https://github.com/testcontainers/testcontainers-python (pyproject.toml, CHANGELOG.md, docs/modules/neo4j.md, commit 6146aa1)
- [S76] testcontainers-4.15.0-py3-none-any.whl downloaded from PyPI (files testcontainers/neo4j.py and testcontainers/community/neo4j/__init__.py)
- [S77] https://neo4j.com/docs/browser-manual/current/deployment-modes/neo4j-server/
- [S78] https://neo4j.com/docs/browser-manual/current/
- [S79] https://neo4j.com/docs/bloom-user-guide/current/bloom-installation/
- Also consulted (no facts cited beyond those above): https://community.neo4j.com/t/neo4j-2026-releases/76512, https://community.neo4j.com/t/neo4j-docker-in-github-action/25622, https://neo4j.com/docs/operations-manual/current/installation/requirements/, https://neo4j.com/licensing/, https://neo4j.com/docs/graph-data-science-client/current/installation/, https://neo4j.com/docs/apoc/current/overview/apoc.periodic/apoc.periodic.iterate/ (2026.06 version), https://neo4j.com/docs/getting-started/data-import/csv-import/.
