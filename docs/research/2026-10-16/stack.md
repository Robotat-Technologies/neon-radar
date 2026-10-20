# NeonRadar phase 1: software stack verification

Research date: 16 October 2026. Every fact below was checked on 2026-10-16 unless a different date is given. Each fact carries a source ID in square brackets; the full URL of every source is in the "Sources" list at the end, each with its check date. Facts that could not be confirmed against an official source are marked UNVERIFIED.

Scope: an open-source (Apache-2.0), local-first anti-money-laundering knowledge graph, Neo4j Community Edition in Docker, Python backend, Vue frontend, an offline LLM copilot, built mostly by AI coding agents and reviewed by humans. Plan context taken from `plan-extract.md` (Neo4j 5.x, Python 3.11+, Vue 3 + Vite + Cytoscape.js, Splink, 500k nodes / 2M relationships on a 16 GB laptop, small-dataset mode for weak laptops, devcontainer plus Codespaces).

## How this was verified (read this first)

- Package versions: PyPI JSON API (`https://pypi.org/pypi/<name>/json`) and the npm registry (`https://registry.npmjs.org/<name>`), queried directly. Several wheels and tarballs were downloaded and inspected (testcontainers, neo4j-graphrag, splink, rigour, @neo4j-nvl/base, create-vue, cytoscape).
- GitHub projects: release tags listed with `git ls-remote` against the official repositories; tag dates from shallow fetches; files read from `raw.githubusercontent.com`; several official repos cloned read-only (neo4j/docs-operations, neo4j/docs-cypher, neo4j/docs-drivers, neo4j/docker-neo4j, neo4j/graph-data-science, neo4j/graph-data-science-client, neo4j/neo4j-python-driver, neo4j/neo4j-graphrag-python, neo4j/apoc, testcontainers/testcontainers-python, github/docs, docker/docs).
- Neo4j documentation was verified from its AsciiDoc sources in the official docs repositories, which are what `neo4j.com/docs` is built from. The `dev` branch of docs-operations and docs-cypher is already labelled 2026.10 (an unreleased version), so a few statements describe the next release; this is flagged where it matters.
- Access limits on 2026-10-16: the web fetch tool was rate-limited (HTTP 429) for `hub.docker.com/v2/repositories/library/neo4j/tags`, `neo4j.com/release-notes/database/` and `github.com/docker/compose/releases/tag/v5.0.0`; direct HTTPS to neo4j.com, hub.docker.com, huggingface.co, ollama.com, nodejs.org, docs.python.org and gnu.org was refused by the egress proxy. Equivalent official sources were used instead (Docker official-images manifest, docs source repos, PEP sources, nodejs/Release schedule). Facts that only those blocked sites could confirm are marked UNVERIFIED.

---

## 1. Neo4j

### 1.1 Release lines and versioning

- Neo4j moved to calendar versioning in 2025: "releases from 2025 onwards will follow a YYYY.MM format, beginning with version 2025.01 released in January 2025". Confirmed. [S6]
- Release tags in the Community Edition source repository (neo4j/neo4j) run 2025.01.0 through 2026.09.0; there is no 2026.10 tag yet. The newest calendar release is **2026.09.0** (tag commit 2026-09-14). The newest 5.x release is **5.26.32** (tag commit 2026-10-06, a CVE fix release). [S2]
- 5.26 is the long-term-support line. Neo4j's policy: "Breaking changes are only made in the release immediately following a long-term support (LTS) release" and "Deprecated features are only removed immediately after a long-term support (LTS) release". [S13]
- A new LTS is coming: the Operations Manual repeatedly refers to "the next LTS release in 2026". Exact version number and date of the 2026 LTS: UNVERIFIED (not published in the sources reachable today). [S13]
- 5.26 LTS end-of-support date: UNVERIFIED (the Neo4j blog page that states it could not be fetched).
- Implication: the plan's "Neo4j 5.x" is no longer the current line. 5.26 is a frozen maintenance line (Cypher 5 only); new features land only in 2025.x/2026.x and only in Cypher 25.
- Java: the official 2026.09.0 image is built `FROM debian:trixie-slim` with Java copied from `eclipse-temurin:25`; the 5.26.32 image uses `eclipse-temurin:21`. [S3]

### 1.2 Docker image tags (official `neo4j` image)

From the Docker official-images manifest for `neo4j` (the authoritative tag list for Docker Hub "library" images) [S1]:

| Line | Community tags (all equivalent) | Notes |
|---|---|---|
| 2026.09.0 (current) | `2026.09.0-community`, `2026.09-community`, `2026-community`, `community`, `latest`, `2026.09.0`, `2026.09`, `2026`, plus `-trixie` and `-ubi10` variants | amd64 and arm64v8 |
| 5.26.32 (LTS) | `5.26.32-community`, `5.26-community`, `5-community`, `5.26.32`, `5.26`, `5`, plus `-trixie`/`-ubi10` | amd64 and arm64v8 |
| 4.4.48 | `4.4.48-community`, `4.4-community` | legacy |

- Recommended pin: **`neo4j:2026.09.0-community`** (exact tag, never `latest`), and move to the 2026 LTS tag once it is published. Conservative alternative: `neo4j:5.26.32-community` if the team wants an LTS today and accepts Cypher 5 only (no `ACYCLIC`, no `SEARCH` clause) plus a later migration.
- The image has **no built-in HEALTHCHECK**, exposes 7474, 7473 and 7687, declares volumes `/data` and `/logs`, keeps `wget` but purges `curl` (so `curl`-based healthchecks fail). [S3]
- The entrypoint defaults `server.memory.pagecache.size` to 512M and `server.default_listen_address` to 0.0.0.0 unless you set them; heap is not set by the entrypoint. [S4]

### 1.3 Graph Data Science (GDS) with Community Edition

- GDS Community Edition is supported on Neo4j Community Edition (edition table: "Support for Neo4j Graph Data Science Community Edition": CE yes). [S10]
- GDS CE limits (GDS docs, tag 2026.09.0) [S25][S26]:
  - includes all algorithms;
  - concurrency limited to **maximum 4 CPU cores** ("The maximum concurrency limit ... is not set based on your edition of the Neo4j database", it depends on whether you hold a GDS EE licence);
  - model catalog limited to **3 models**; no model persistence to disk, no model publishing;
  - no graph catalog backup/restore, no Apache Arrow import/export, no optimized ("bit id map") graph implementation, no configurable defaults and limits, no cluster write workloads.
- GDS versioning also changed: GDS 2.14 to 2.27 paired with Neo4j 2025.01 to 2026.02, then GDS switched to calendar versions matching Neo4j from 2026.03. Current GDS: **2026.09.0** (tag commit 2026-09-15); 5.26 LTS pairs with GDS 2.13 (latest tag 2.13.14, 2026-10-08). [S29]
- Official compatibility matrix (GDS docs, `supported-neo4j-versions.adoc` at tag 2026.09.0) [S24]:

| Neo4j | GDS |
|---|---|
| 2026.09.0 | 2026.09 |
| 2026.08.1 | 2026.08 |
| 2026.07.0 | 2026.07 |
| 2026.06.0 | 2026.06 |
| 2026.05.0 | 2026.05 |
| 2026.04.0 | 2026.04 |
| 2026.03.0 | 2026.03 |
| 2026.02.0 | 2.27 |
| 2026.01.4 | 2.26 |
| 2025.12.1 | 2.25 |
| 2025.11.2 | 2.24 |
| 2025.10.1 | 2.23 |
| 2025.09 ... 2025.01 | 2.22 ... 2.14 |
| 5.26 | 2.13 |
| 4.4.9 or later | 2.6 |

- "In general, the latest version of GDS supports the latest version of Neo4j and vice versa." [S24]
- GDS 2026.09.0 is compiled to Java 21 bytecode (Gradle toolchain `JavaLanguageVersion.of(21)`), which runs on the image's Java 25 runtime. [S28]
- GDS memory: projections and algorithm state live on the JVM heap; for analytical workloads GDS docs recommend shifting memory from page cache to heap, but warn not to do that when the instance serves operational and analytical work at the same time; use `gds.graph.project.estimate(...)` / `<algo>.estimate` to size the heap. [S26]

### 1.4 Enabling APOC Core and GDS in the official Docker image

- `NEO4J_PLUGINS` takes a JSON list. The docs list `apoc`, `apoc-extended`, `bloom`, `genai`, `graph-data-science`, `n10s` as known names (e.g. `"gds"` is rejected as unknown); the plugin manifest inside the 2026.09.0 image actually contains `apoc`, `apoc-extended`, `bloom`, `genai`, `graph-data-science` and `fleet-management` (no `n10s`). Example from the docs: `--env NEO4J_PLUGINS='["apoc", "graph-data-science"]'`. Neo4j labels this utility as intended for development, not production. [S7][S3]
- **APOC Core is bundled inside the image** (`/var/lib/neo4j/labs/apoc-*-core.jar`) for both editions since 5.0, so `apoc` installs offline. [S4][S5]
- **GDS is bundled only in Enterprise images** (`/var/lib/neo4j/products/...`). In the Community image the entrypoint downloads it at container start using `https://graphdatascience.ninja/versions.json`. [S4][S5]
- Offline consequence (local-first requirement): if the download fails, the entrypoint logs an error, starts Neo4j without GDS, and also skips writing `dbms.security.procedures.unrestricted=gds.*`. [S4] Mitigation: mount a `/plugins` volume so the downloaded jars persist (documented pattern: download once with `NEO4J_PLUGINS`, then start later "without needing to set NEO4J_PLUGINS") [S7], and set `NEO4J_dbms_security_procedures_unrestricted=apoc.*,gds.*` explicitly.
- APOC settings passed as `NEO4J_apoc_*` environment variables are written to `conf/apoc.conf`, not `neo4j.conf` (for example `NEO4J_apoc_export_file_enabled=true`). [S4]
- APOC Core licence: Apache-2.0. [S31]

### 1.5 Environment variables: naming, memory, auth

- Naming rule: prefix `NEO4J_`, write `_` as `__`, write `.` as `_`. [S8][S4]
  - `server.memory.heap.initial_size` -> `NEO4J_server_memory_heap_initial__size`
  - `server.memory.heap.max_size` -> `NEO4J_server_memory_heap_max__size` (confirmed)
  - `server.memory.pagecache.size` -> `NEO4J_server_memory_pagecache_size` (confirmed)
  - `db.query.default_language` -> `NEO4J_db_query_default__language`
- `neo4j-admin server memory-recommendation --memory=16g --docker` prints these exact variables (docs example output: heap 5g/5g, page cache 7g, plus `NEO4J_server_jvm_additional='-XX:+ExitOnOutOfMemoryError'`). That example assumes a machine dedicated to Neo4j. [S9]
- Set initial and max heap to the same value "to avoid unwanted full garbage collection pauses"; reserve about 1 GB for the OS on a dedicated server; vector index files live in the OS file-system cache, not the page cache, so leave RAM for the OS if you use vector indexes. [S11]
- `NEO4J_AUTH` [S4][S16]:
  - format `neo4j/<password>`; the user must be `neo4j`; the password cannot be `neo4j`; minimum length 8 characters (override with `NEO4J_dbms_security_auth__minimum__password__length`);
  - optional `/true` suffix forces a password change on first login;
  - `NEO4J_AUTH=none` disables authentication;
  - Docker secrets: any `NEO4J_*_FILE` variable is read from a file (recommended `NEO4J_AUTH_FILE=/run/secrets/...`), and a secret overrides the plain variable;
  - the password is applied with `neo4j-admin dbms set-initial-password`, i.e. on first initialisation of `/data`; changing `NEO4J_AUTH` later does not change an existing database's password (this follows from the "initial password" mechanism; behaviour on an existing volume not tested here).

### 1.6 Cypher: constraints and indexes (Community vs Enterprise)

Edition table [S10] and Cypher manual labels [S17]:

| Feature | Community | Syntax |
|---|---|---|
| Property uniqueness constraint (single or composite, node or relationship) | Yes | `CREATE CONSTRAINT company_id IF NOT EXISTS FOR (c:Company) REQUIRE c.company_id IS UNIQUE` |
| Property existence constraint | **No (Enterprise)** | `... REQUIRE n.prop IS NOT NULL` |
| Property type constraint | **No (Enterprise)** | `... REQUIRE n.prop IS :: STRING` |
| Node / relationship key constraint | **No (Enterprise)** | `... REQUIRE (n.a, n.b) IS NODE KEY` / `IS RELATIONSHIP KEY` |
| Range, text, point, composite indexes | Yes | `CREATE INDEX txn_date IF NOT EXISTS FOR ()-[t:TRANSFER]-() ON (t.date)` |
| Full-text indexes | Yes | see below |
| Vector indexes | Yes | see below |

- Consequence: "must exist" and "must be a STRING" rules cannot be enforced in the database on CE. Enforce them in the loader (pydantic models) and in tests, and use uniqueness constraints for every business key.
- `IF NOT EXISTS` makes constraint and index creation idempotent (no error, informational notification). [S17][S18]
- Specifying an `indexProvider` in `OPTIONS` is no longer supported in Cypher 25. [S23]

Full-text [S18][S20]:

```cypher
CREATE FULLTEXT INDEX entityNames IF NOT EXISTS
FOR (n:Person|Company) ON EACH [n.name, n.alias]
OPTIONS { indexConfig: { `fulltext.analyzer`: 'standard-no-stop-words' } };

// Cypher 25, Neo4j 2026.09+: SEARCH clause (preferred)
MATCH (node)
  SEARCH node IN (FULLTEXT INDEX entityNames FOR "al rashid" LIMIT 20)
  SCORE AS score
RETURN node.name, score;

// Works on all versions (deprecated in the 2026.10 docs):
CALL db.index.fulltext.queryNodes("entityNames", "al rashid") YIELD node, score
RETURN node.name, score;
```

- Default analyzer is `standard-no-stop-words`; list analyzers with `CALL db.index.fulltext.listAvailableAnalyzers()`. [S18]
- `SEARCH` with full-text is "new in Neo4j 2026.09" and Cypher 25 only; the 2026.10 docs mark `db.index.fulltext.queryNodes/queryRelationships` as deprecated in favour of it. [S18][S23]

Vector [S19][S20]:

```cypher
CREATE VECTOR INDEX entityEmbedding IF NOT EXISTS
FOR (n:Entity) ON n.embedding
OPTIONS { indexConfig: { `vector.dimensions`: 384, `vector.similarity_function`: 'cosine' } };

MATCH (q:Entity {id: $id})
MATCH (n:Entity)
  SEARCH n IN (VECTOR INDEX entityEmbedding FOR q.embedding LIMIT 10) SCORE AS score
RETURN n, score;
```

- Vector indexes are available in Community. [S10] `SEARCH` for vector indexes exists from 2026.01; `db.index.vector.queryNodes()` was deprecated in 2026.04. [S20][S23] New quantization settings arrived in 2026.06/2026.07. [S19]

### 1.7 Cypher 25, GQL and variable-length traversals

- Cypher 25 was introduced with Neo4j 2025.06 as a clone of Cypher 5 plus new features; "Any new Cypher features introduced in Neo4j 2025.06 or later will be exclusively added to Cypher 25"; Cypher 5 is frozen at its 2025.06 state. [S6]
- Default language: databases created on Neo4j 2026.02 or later get `db.query.default_language=CYPHER_25` written into `neo4j.conf`; if the setting is missing the default is `CYPHER_5`. A query can override with a `CYPHER 25` or `CYPHER 5` prefix. [S6] Recommendation: set `NEO4J_db_query_default__language=CYPHER_25` explicitly in Compose so behaviour does not depend on how the volume was created.
- Cypher 25 removals that AI-generated code can trip over: `SET n = r` with a node or relationship on the right-hand side (use `properties(r)`), cross-entity property references inside one `MERGE`, `indexProvider` options, several old procedures (`db.index.vector.createNodeIndex`, `db.create.setVectorProperty`). [S23]
- Quantified path patterns (QPP) and quantified relationships are the modern syntax for variable-length traversal (`-[:R]->{1,6}`, `((a)-[:R]->(b)){1,6}`, `-[:R]->+`); variables inside a QPP become lists ("group variables"). [S21]
- Path modes (GQL-conformant) are new in Neo4j 2026.03, Cypher 25 only: `WALK`, `TRAIL`, `ACYCLIC`. `ACYCLIC` forbids repeated nodes within a path and prunes during evaluation, which the docs describe as "significantly more efficient" than post-filtering. Path modes cannot be combined with the old `[*1..6]` syntax (error 51N26) and cannot be used in `MERGE`. Declaring the same node variable twice inside one `ACYCLIC` path yields no matches. Match mode `REPEATABLE ELEMENTS` (2025.06, Cypher 25) allows repeated relationships with bounded quantifiers. [S22]

AML patterns (sketches based on the documented syntax):

```cypher
// Beneficial-ownership chains, effective share, no node revisited (Cypher 25, 2026.03+)
CYPHER 25
MATCH p = ACYCLIC (owner:Person)-[o:OWNS]->{1,6}(c:Company {company_id: $id})
RETURN owner.name, reduce(s = 1.0, r IN o | s * r.share) AS effective_share
ORDER BY effective_share DESC;

// Round-tripping funds: closed trails back to the start account (default DIFFERENT RELATIONSHIPS mode)
MATCH p = (a:Account)-[t:TRANSFER]->{2,6}(a)
WHERE all(i IN range(0, size(t) - 2) WHERE t[i].ts < t[i + 1].ts)   // time-ordered hops
RETURN p LIMIT 50;

// Simple cycle with no repeated intermediate account: ACYCLIC path joined to a closing hop.
// All path patterns in one MATCH must use the same path mode, so both carry ACYCLIC.
CYPHER 25
MATCH p = ACYCLIC (a:Account)-[:TRANSFER]->{1,5}(z:Account),
      q = ACYCLIC (z)-[:TRANSFER]->(a)
RETURN p, q LIMIT 50;
```

The equijoin form (repeating a node variable across two `ACYCLIC` path patterns in one `MATCH`) is documented as allowed; mixing different path modes in one `MATCH` is an error (42N61, "Split the pattern into separate MATCH clauses instead"). Since 2026.05 explicit path modes can also be combined with `ANY SHORTEST` style selectors. [S22] Performance of these queries on the 500k/2M benchmark is untested.

### 1.8 Licences and the Apache-2.0 question

- Neo4j Community Edition: GPLv3 ("Neo4j Community Edition is an open source product licensed under GPLv3"; the repository `LICENSE.txt` is GPL v3; the edition table says "Open source under GPLv3"). [S30][S10]
- GDS: the repository `LICENSE.txt` grants GPLv3 "to all third parties" unless a commercial agreement applies, and the sources can be built as "OpenGDS" under GPLv3. However the README states that GDS "as built and distributed by Neo4j includes the sources in this repository as well a suite of closed sources" and is used "under the constraints of its license". The exact licence text shipped with the downloadable GDS CE jar: UNVERIFIED (the download pages were not reachable). [S28]
- APOC Core: Apache-2.0. [S31] Neo4j Python driver: `Apache-2.0 AND Python-2.0` (PyPI licence expression). [S32] graphdatascience client and neo4j-graphrag: Apache-2.0. [S35][S36]
- Implication for an Apache-2.0 project that only talks to Neo4j over Bolt (analysis, not legal advice):
  - GPLv3 (not AGPL) obligations attach to conveying the GPL program. Running Neo4j and calling it over a network socket from separate code is the textbook "separate programs communicating at arm's length" case in the FSF GPL FAQ, so the application code can stay Apache-2.0. The FAQ itself could not be re-fetched today (gnu.org blocked): UNVERIFIED re-check of https://www.gnu.org/licenses/gpl-faq.html#MereAggregation.
  - A Compose file that references `neo4j:2026.09.0-community` and lets the user pull it, with GDS downloaded at runtime by the official entrypoint, does not redistribute Neo4j or GDS.
  - Do not publish your own image with Neo4j and the GDS jar baked in unless someone has read the GDS distribution terms; that would make the project a distributor (GPLv3 obligations for Neo4j, plus whatever applies to the closed parts of the GDS jar).
  - Do not write custom Java procedures/plugins that load into the Neo4j server; keep logic in Cypher, APOC or the Python app.
  - Neo4j Visualization Library (NVL) is a separate problem: it is proprietary and restricted to Aura and Enterprise customers (see section 5).

---

## 2. Neo4j Python driver, bulk loading, GDS client

### 2.1 `neo4j` driver

- Current: **neo4j 6.4.1** (PyPI, 2026-10-15), `requires_python >=3.10`, classifiers 3.10 to 3.15, licence `Apache-2.0 AND Python-2.0`. 6.0.0 was released 2025-09-30. [S32]
- `neo4j-driver` is the old name: "It is now deprecated and will receive no further updates starting with 6.0.0". (The 5.x line still gets patches under both names; `neo4j-driver` 5.28.8 and `neo4j` 5.28.8 were both uploaded 2026-10-15.) [S33][S32]
- The 6.x driver supports Neo4j 4.4, 5.x, 2025.x and 2026.x. [S34]
- Driver 6.0 breaking changes worth telling agents about: Python 3.7 to 3.9 dropped; `session.read_transaction` / `session.write_transaction` removed (use `execute_read` / `execute_write`); `neo4j.Bookmark` and `session.last_bookmark()` removed; `trust` config option removed; several deprecated modules removed; client-side errors now raise `DriverError` subclasses rather than `ClientError`. 6.4 deprecates URIs with a path or fragment. [S33]
- Optional speed-up: `neo4j-rust-ext` 6.4.1.0 (same API, 3x to 10x claimed), wheels for CPython 3.10 to 3.15. [S34][S39]

Recommended usage (from the Python driver manual) [S34]:

```python
from neo4j import GraphDatabase, RoutingControl

with GraphDatabase.driver("neo4j://localhost:7687", auth=("neo4j", password)) as driver:
    driver.verify_connectivity()

    # 1) Simple queries: execute_query (automatic retries, eager result)
    records, summary, keys = driver.execute_query(
        "MATCH (c:Company {company_id: $id}) RETURN c.name AS name",
        id=company_id, database_="neo4j", routing_=RoutingControl.READ,
    )

    # 2) Bulk writes: UNWIND a list parameter inside a managed transaction
    def load_companies(tx, rows):
        tx.run(
            "UNWIND $rows AS row "
            "MERGE (c:Company {company_id: row.id}) SET c.name = row.name",
            rows=rows,
        )

    with driver.session(database="neo4j") as session:
        for batch in batches(rows, 10_000):      # batch size is a tuning choice
            session.execute_write(load_companies, batch)
```

- "Batch queries when creating a lot of records using the WITH and UNWIND Cypher clauses"; always pass `database_`; always use query parameters; `execute_query` is eager, so use `execute_read`/`execute_write` and iterate the result for large result sets. [S34]
- Managed transactions (`execute_read`/`execute_write`) retry on transient errors, so transaction functions must be idempotent. `execute_query` also retries transient failures. [S34]

### 2.2 `neo4j-admin database import full` (bulk CSV) in Docker

- Run inside the container image: `docker run ... neo4j:<tag> neo4j-admin database import full --nodes=... --relationships=... <database>`; CSV files go in the folder mounted at `/import` and must follow the import header format. [S9]
- It is an offline import "into a non-existent or empty database"; an existing database requires `--overwrite-destination` (which deletes it first). Community Edition supports full import; incremental import is Enterprise-only, and the `--schema` option (create indexes and constraints during import, 2025.02+) is Enterprise-only. [S14][S10]
- Practical shape for this project (stop the running `neo4j` service first, since the store must not be in use):

```bash
docker compose stop neo4j
docker compose run --rm neo4j neo4j-admin database import full \
  --nodes=Company=/import/company_header.csv,/import/company.csv \
  --nodes=Person=/import/person_header.csv,/import/person.csv \
  --relationships=OWNS=/import/owns_header.csv,/import/owns.csv \
  --overwrite-destination neo4j
docker compose start neo4j    # then create constraints and indexes with Cypher
```

  Whether `--overwrite-destination` alone is sufficient for the default `neo4j` database on a previously used volume was not tested.

### 2.3 `graphdatascience` Python client

- Current: **graphdatascience 2.2** (2026-10-14), Python `>=3.10, <3.15`, Apache-2.0. [S35][S39]
- Compatibility (client docs): client 2.1 to 2.3 support GDS `>= 2.13, < 2.28` and calendar GDS `< 2026.10`; driver `>= 5.26.0, < 7.0.0`. So 2.2 covers both GDS 2.13 (Neo4j 5.26) and GDS 2026.09. [S35]
- **Client 2.0 (2026-09-18) made the "V2 API" the only API**: snake_case endpoints (`gds.page_rank.stream(G, damping_factor=0.85)` instead of `gds.pageRank.stream(G, dampingFactor=0.85)`), no `gds.alpha`/`gds.beta` prefixes, typed result objects instead of pandas Series, changed projection endpoints. Most examples on the web and in model training data use the 1.x API. [S35]
- Alternative that sidesteps client churn: call GDS procedures in Cypher through the driver (`CALL gds.pageRank.stream(...)`), which is the stable public surface.

---

## 3. Python tooling

### 3.1 Which Python to pin

- Python **3.15.0** was released 2026-10-09 (PEP 790 schedule; tag `v3.15.0`). [S37][S38]
- Python **3.14.8** is the current 3.14 patch (2026-09-30); 3.14 gets bugfix releases until 3.14.14 in October 2027. [S37][S38]
- Python 3.13.16 (2026-10-01) was "Final regular bugfix release with binary installers"; 3.13 is now source-only security fixes. [S37]
- Library support for 3.15 is not there yet: `neo4j-graphrag` requires `<3.15`, `graphdatascience` requires `<3.15`, and `duckdb` 1.5.6 (required by Splink) ships wheels only up to cp314. [S36][S35][S39]
- Every compiled dependency checked has cp314 wheels: duckdb, rigour, jellyfish, rapidfuzz, pydantic-core, pyarrow 26, numpy 2.5, scikit-learn 1.9.1, neo4j-rust-ext; polars 2.0 uses an abi3 runtime wheel. [S39]
- Recommendation: **pin Python 3.14** (`requires-python = ">=3.14,<3.15"` and `.python-version` = `3.14`). The plan's "3.11+" floor is outdated: numpy 2.5 no longer ships 3.10/3.11 wheels, pandas 3 and pre-commit 4.7 need 3.11+, rapidfuzz needs 3.11+. [S39]
- Caveat: the `nlp` extra of neo4j-graphrag (spaCy) is "not supported on Python 3.14"; this project does not need it. [S36]

### 3.2 Versions (PyPI, checked 2026-10-16) [S39]

| Tool | Version (date) | Notes |
|---|---|---|
| uv | 0.13.1 (2026-10-14) | 0.13.0 on 2026-10-09; MIT OR Apache-2.0 |
| ruff | 0.17.1 (2026-10-15) | 0.17.0 on 2026-10-09 |
| mypy | 2.4.0 (2026-10-01) | mypy 2.0 (2026-05-06) enabled `--local-partial-types` and `--strict-bytes` by default and changed `--allow-redefinition` [S45b] |
| pyright | 1.1.414 (2026-09-09/10) | npm package plus PyPI wrapper |
| basedpyright | 1.40.2 (2026-10-04) | |
| ty (Astral) | 0.0.88 (2026-10-15) | "Development Status :: 4 - Beta" |
| pytest | 9.1.1 (2026-06-19) | pytest 9.0.0 on 2025-11-08 |
| pytest-asyncio | 1.4.0 | |
| pytest-cov | 7.1.0 | |
| pydantic | 2.14.1 (2026-10-11) | v2 line continues; 2.14.0 on 2026-10-08 |
| pydantic-settings | 2.16.0 | requires Python 3.11+ |
| FastAPI | 0.143.2 (2026-10-15) | core deps now include `opentelemetry-api` |
| Starlette | 1.8.0 | Starlette 1.0 released 2026-03-22 |
| uvicorn | 0.54.0 | |
| typer | 0.27.3 (2026-10-06) | |
| httpx | 0.28.1 (2024-12-06) | no stable release in 22 months; only `1.0.dev*` pre-releases |
| httpx2 | 2.13.1 (2026-09-23) | Pydantic's continuation of HTTPX, import `httpx2` [S43] |
| polars | 2.0.0 (2026-10-06) | major release ten days old; 1.44.2 is the last 1.x |
| pandas | 3.0.6 (2026-09-17) | 3.0.0 on 2026-01-21; requires Python 3.11+ |
| duckdb | 1.5.6 (2026-09-28) | wheels cp310 to cp314 |
| pyarrow | 26.0.0 (2026-10-09) | |
| testcontainers | 4.15.0 (2026-07-24) | see 3.6 |
| pre-commit | 4.7.0 (2026-10-12) | requires Python 3.11+ |

Recommendations:
- Type checker: mypy 2.x in strict mode (pure-Python install through uv, pydantic plugin available) as the CI gate; basedpyright or pyright as an optional fast editor checker; treat ty as experimental (beta).
- HTTP client: httpx is still pulled in transitively (the `ollama` client requires `httpx>=0.27`; FastAPI's `standard` extra requires `httpx<1.0.0`). Keep it for tests and the Ollama client. For new direct HTTP code either is fine; note that HTTPX upstream has "limited activity" and Pydantic took over stewardship as httpx2 (Starlette 1.8's `full` extra lists both `httpx2>=2.0.0` and `httpx<0.29`). [S43][S39]
- DataFrames: Splink 5 needs only DuckDB and PyArrow (section 4), so the lightest stack is DuckDB SQL plus PyArrow for ETL. If a dataframe library is wanted, pick polars but pin `polars>=1.44,<2` for phase 1 (2.0 is ten days old) or `polars==2.0.*` deliberately; pandas 3 brings its own behaviour changes (copy-on-write and the new default string dtype, UNVERIFIED details since the pandas docs were not fetched).

### 3.3 uv project layout with workspaces

- A workspace is declared with `[tool.uv.workspace]` (`members` globs required, `exclude` optional) in the root `pyproject.toml`; all members share one `uv.lock`; `uv run --package <member>` targets a member; member-to-member dependencies use `[tool.uv.sources] name = { workspace = true }` and are editable. [S40]
- uv enforces one `requires-python` for the whole workspace (the intersection of members). Workspaces are "not suited for cases in which members have conflicting requirements"; path dependencies are the alternative. [S40]
- uv's own build backend: `requires = ["uv_build>=0.13.1,<0.14"]`, `build-backend = "uv_build"`. [S40]
- Docker: copy uv from `ghcr.io/astral-sh/uv:0.13.1`, or start from `ghcr.io/astral-sh/uv:python3.14-trixie`. [S41]

Suggested layout for this repo (the plan's `/ui`, `/copilot` folders map onto it):

```text
neonradar/
├── pyproject.toml          # [tool.uv.workspace] members = ["packages/*"]; requires-python = ">=3.14,<3.15"
├── uv.lock
├── .python-version         # 3.14
├── packages/
│   ├── schema/             # pydantic models, graph schema, constraint DDL (the frozen contract)
│   ├── ingest/             # loaders -> intermediate records -> CSV for neo4j-admin / UNWIND batches
│   ├── resolve/            # Splink + rigour/normality name handling
│   ├── detect/             # typology Cypher + GDS jobs + evaluation harness
│   ├── copilot/            # templates, text-to-Cypher fallback, grounding
│   └── api/                # FastAPI app
├── ui/                     # Vue app (npm, separate lockfile)
├── compose.yaml
└── .devcontainer/
```

### 3.4 Linting, formatting, hooks

- ruff-pre-commit `v0.17.1` provides hook ids `ruff-check` and `ruff-format` (`ruff` is the legacy alias). uv-pre-commit `0.13.1` provides `uv-lock`, `uv-export`, `uv-sync`, `uv-audit`. gitleaks `v8.30.1` provides `gitleaks`. [S78]

### 3.5 PyICU build requirement (affects devcontainer, CI and Windows/macOS contributors)

- normality 3.x: "requires `pyicu` as a mandatory dependency". rigour, followthemoney, fingerprints and nomenklatura all depend on normality 3.x. [S48][S47]
- PyICU 2.16.2 publishes **no wheels on PyPI**, only an sdist; building needs `pkg-config` plus ICU headers and libraries (Debian/Ubuntu: `pkg-config libicu-dev` and a C++ toolchain; macOS: Homebrew `icu4c` with `PKG_CONFIG_PATH`). [S50]
- Put `apt-get install -y pkg-config libicu-dev build-essential` in the devcontainer Dockerfile and CI, and test Windows contributors early (or route them to the devcontainer).

### 3.6 testcontainers-python and Neo4j

- testcontainers 4.15.0 (2026-07-24), Python `>=3.10`, Apache-2.0. The Neo4j module now lives at **`testcontainers.community.neo4j`**; `testcontainers.neo4j` still imports but emits a `DeprecationWarning`. Install with the `neo4j` extra, which requires `neo4j>=6`. Verified in the released wheel. [S42]
- `Neo4jContainer(image="neo4j:latest", password=...)` sets `NEO4J_AUTH`, waits for the log line "Remote interface available at", then calls `driver.verify_connectivity()`. Always pass the pinned image tag; add GDS with `.with_env("NEO4J_PLUGINS", '["apoc","graph-data-science"]')` (needs network for the GDS download). [S42]

```python
from testcontainers.community.neo4j import Neo4jContainer

with Neo4jContainer("neo4j:2026.09.0-community", password="test-password-1") as neo4j, \
        neo4j.get_driver() as driver:
    driver.execute_query("RETURN 1")
```

---

## 4. Entity resolution

### 4.1 Splink: version 5, not 4

- Current: **splink 5.0.0**, released **2026-09-28**; MIT; `requires_python >=3.10,<4.0`; pure-Python wheel. [S44][S39]
- Runtime dependencies are now only `duckdb`, `pyarrow` and `sqlglot`; pandas, NumPy, Altair, igraph and Jinja2 are optional (extras: `altair`, `igraph`, `postgres`, `spark`/`pyspark`, `sqlite`). Backends shipped: DuckDB (default in examples), Spark, PostgreSQL, SQLite; Amazon Athena support was removed. [S44][S45]
- "There has been no change to the statistical model" and v4 JSON models load in v5, but "Splink 5 syntax is not fully backwards compatible". Key breaking changes [S44]:
  - inputs must be registered first: `sdf = db_api.register(df, dataset_display_name="...")`; `Linker(...)` no longer takes `db_api=`;
  - output columns use match weights with prefix `mw_` instead of Bayes factors `bf_` (`bayes_factor_column_prefix` deprecated);
  - `compare_two_records()` and `find_matches_to_new_records()` removed (use `score_pair()`, `score_pairs()`, `predict_within()`, `predict_between()`); salting, implicit caching and `use_cache` removed;
  - `as_record_dict()` renamed `as_record_list()`; `query_sql()` returns a `SplinkDataFrame`;
  - `DateOfBirthComparison` now uses standard Levenshtein on all backends.
- The Splink team publishes an LLM prompt for upgrading v4 code (linked from the release post), which is useful because coding agents will default to v4 syntax. [S44]
- The plan's previous assumption (v4 API) needs updating: either pin `splink==5.0.*` and give agents the v5 notes, or deliberately pin `splink==4.0.16` (last v4, 2026-03-11). For a 28-day project starting now, v5 is the better choice (smaller install, no pandas needed).

Configuring names and dates (signatures read from the 5.0.0 wheel) [S45]:

- `cl.NameComparison(col, jaro_winkler_thresholds=[0.92, 0.88, 0.7], dmeta_col_name=None)`: levels null, exact, Jaro-Winkler > 0.92 / > 0.88 / > 0.70, else; optional double-metaphone array column.
- `cl.ForenameSurnameComparison(forename_col, surname_col, jaro_winkler_thresholds=[0.92, 0.88], forename_surname_concat_col_name=None)`: includes a "columns reversed" level (useful for name-order swaps common in transliterated Arabic and East Asian names).
- `cl.DateOfBirthComparison(col, input_is_string=..., datetime_thresholds=[1, 1, 10], datetime_metrics=["month", "year", "year"], datetime_format=None, invalid_dates_as_null=True)`: levels exact, Levenshtein <= 1, within 1 month, 1 year, 10 years, else. `input_is_string` is required.
- Also available: `JaroWinklerAtThresholds`, `LevenshteinAtThresholds`, `DamerauLevenshteinAtThresholds`, `JaccardAtThresholds`, `ExactMatch(...).configure(term_frequency_adjustments=True)`, `ArrayIntersectAtSizes`, `PostcodeComparison`, `EmailComparison`, `CosineSimilarityAtThresholds`, `CustomComparison`.

```python
import splink.comparison_library as cl
from splink import DuckDBAPI, Linker, SettingsCreator, block_on

db_api = DuckDBAPI()
people = db_api.register(people_table, dataset_display_name="people")   # pyarrow / duckdb / pandas input

settings = SettingsCreator(
    link_type="dedupe_only",
    comparisons=[
        cl.NameComparison("name_norm"),
        cl.DateOfBirthComparison("dob", input_is_string=True),
        cl.ExactMatch("country").configure(term_frequency_adjustments=True),
    ],
    blocking_rules_to_generate_predictions=[block_on("surname_norm"), block_on("dob")],
)
linker = Linker(people, settings)
linker.training.estimate_probability_two_random_records_match([block_on("name_norm", "dob")], recall=0.7)
linker.training.estimate_u_using_random_sampling(max_pairs=1e6)
linker.training.estimate_parameters_using_expectation_maximisation(block_on("dob"))
pairs = linker.inference.predict(threshold_match_probability=0.5)
clusters = linker.clustering.cluster_pairwise_predictions_at_threshold(pairs, 0.95)
```

How matches are reported: `predict()` returns pairwise rows with `match_weight` (log-odds) and `match_probability`, plus per-comparison `mw_<name>` columns; it accepts `threshold_match_probability` or `threshold_match_weight`; clustering then groups pairs above a probability threshold. [S45][S46]

Evaluating precision with labelled pairs [S45]:

```python
labels = db_api.register(labels_table, dataset_display_name="labels")
# columns: unique_id_l, unique_id_r, clerical_match_score (plus source_dataset_l/_r for link jobs)
labels = linker.table_management.register_labels_table(labels)
truth = linker.evaluation.accuracy_analysis_from_labels_table(
    labels, output_type="table", threshold_match_probability=0.5, add_metrics=["f1"]
)
errors = linker.evaluation.prediction_errors_from_labels_table(labels)
```

`output_type` can be `"threshold_selection"` (default chart), `"roc"`, `"precision_recall"`, `"accuracy"` or `"table"`; precision and recall are always included; extra metrics include specificity, npv, accuracy, f1, f2, f0_5, p4 and phi. If ground truth is a cluster id column, use `accuracy_analysis_from_labels_column`. [S45] This directly supports the plan's "accept roughly 80% precision and publish the number".

### 4.2 OpenSanctions libraries

| Library | Version (date) | Licence | Notes |
|---|---|---|---|
| rigour | 2.5.0 (2026-09-10) | MIT | Rust core, wheels cp310 to cp314; depends on normality 3.x (so on PyICU) [S47][S39] |
| nomenklatura | 4.17.2 (2026-10-12) | MIT | heavy: duckdb, followthemoney, rigour, scikit-learn==1.9.1 (exact pin), sqlalchemy, textual, lxml; requires Python 3.11+ [S39] |
| followthemoney | 4.11.0 (2026-09-03) | MIT | the FtM entity model used by OpenSanctions/Aleph [S39] |
| normality | 3.1.0 (2026-03-08) | MIT | PyICU mandatory since 3.0 [S48] |
| fingerprints | 1.3.1 (2025-08-01) | MIT | **UNMAINTAINED**: "the next generation of the fingerprints codebase is now included in rigour ... This library is now UNMAINTAINED" [S49] |

What rigour 2.5.0 provides (read from the sdist) [S47]:
- `rigour.names`: `analyze_names` (raw strings to tagged `Name` objects, person prefix stripping, organisation legal-form replacement), `tokenize_name`, `normalize_name`, `align_person_name_order`, `pick_name`, `compare_parts` (residue-distance scoring of name parts with a typo budget; documented "strict (payment-screening)" vs "permissive (KYC-onboarding)" profiles via `CompareConfig`).
- `rigour.text`: `levenshtein`, `jaro_winkler`, `metaphone`, `soundex`, Unicode script detection (ICU4X), and `maybe_ascii` / `should_ascii` transliteration.
- Important limit: rigour's transliteration "covers only six admitted scripts (Latin, Cyrillic, Greek, Armenian, Georgian, Hangul)". For Arabic and other scripts the module says to use `normality.ascii_text` / `normality.latinize_text` (ICU based). [S47]
- Recommendation: use rigour for name analysis and comparison features feeding Splink; do not adopt nomenklatura wholesale in phase 1 (heavy dependency set, its own resolver model).

### 4.3 Transliteration and string-matching libraries

| Library | Version | Licence | Use |
|---|---|---|---|
| PyICU | 2.16.2 | MIT (ICU itself is under the Unicode/ICU licence) | ICU transliterators (standard ICU transform IDs such as `Any-Latin`, `Arabic-Latin`, `Cyrillic-Latin`, `Latin-ASCII`); sdist only, needs libicu [S50] |
| normality | 3.1.0 | MIT | `latinize_text`, `ascii_text`, `normalize` on top of PyICU [S48] |
| anyascii | 0.3.3 | ISC | dependency-free Unicode to ASCII fallback; safe for Apache-2.0 [S39] |
| unidecode | 1.4.0 | **GPL-2.0-or-later** | avoid in an Apache-2.0 codebase [S39] |
| text-unidecode | 1.3 (2019) | Artistic or GPL (dual) | stale; prefer anyascii [S39] |
| jellyfish | 1.2.1 (2025-10-11) | MIT | Jaro-Winkler, Damerau-Levenshtein, Soundex, Metaphone, NYSIIS, Match Rating; wheels to cp314 [S39] |
| rapidfuzz | 3.14.6 (2026-08-30) | MIT | fast fuzzy ratios and `process.cdist` for candidate scoring; Python 3.11+ [S39] |
| camel-tools | 1.6.0 | MIT | Arabic NLP (morphology, Buckwalter transliteration); pulls torch and transformers, too heavy for phase 1 [S39] |
| pyarabic | 0.6.15 (2022) | GPL | avoid (licence and stale) [S39] |

Suggested name pipeline: keep the original-script name; derive `name_latn` with PyICU/normality (`latinize_text`), `name_ascii` with `ascii_text` (or anyascii if PyICU is unavailable), `name_norm` via rigour; feed `name_norm` and a phonetic key (metaphone from rigour or jellyfish) to Splink; use rapidfuzz for quick candidate scoring outside Splink. Arabic-to-Latin output from ICU is a systematic transliteration, not the English spellings used on sanctions lists (for example "Mohammed" vs "Muhammad"); test with real variants before relying on it (quality not measured here).

---

## 5. Frontend

### 5.1 Versions (npm registry) [S51]

| Package | Latest (date) | Notes |
|---|---|---|
| vue | 3.5.44 (2026-10-13) | `rc` tag 3.6.0-rc.11 (2026-10-10); 3.6 not yet stable |
| vite | 8.3.4 (2026-10-08) | Vite 8.0.0 on 2026-03-12; Node `^20.19.0 \|\| >=22.12.0` |
| typescript | 7.0.2 (2026-07-08) is `latest` | 6.0.3 (2026-04-16) is the last 6.x; see 5.3 |
| pinia | 4.1.0 (2026-10-14) | Pinia 4.0.0 on 2026-07-14 |
| vue-router | 5.4.0 (2026-10-07) | Vue Router 5.0.0 on 2026-01-29; peer `vite ^7.3 \|\| ^8`, `pinia ^3.0.4 \|\| ^4.0.2` |
| vitest | 5.0.5 (2026-10-15) | Vitest 5.0.0 on 2026-09-03; Node `^22.12.0 \|\| ^24.0.0 \|\| >=26.0.0`; 4.1.12 still maintained (`V4` tag) |
| @playwright/test | 1.64.1 (2026-10-14) | Node >=20 |
| create-vue | 3.24.0 (2026-09-16) | Node `^22.18.0 \|\| >=24.12.0` |
| @vitejs/plugin-vue | 6.0.10 | supports Vite 5 to 8 and Vue 3.6 rc |
| vue-tsc | 3.3.13 (2026-10-10) | peer `typescript >=5.0.0` |
| eslint | 10.12.0 | |
| typescript-eslint | 8.71.2 | peer `typescript >=4.8.4 <6.1.0` |

What the official scaffold pins today (create-vue 3.24.0 templates) [S52]: `vue ^3.5.42`, `vite ^8.2.2`, `@vitejs/plugin-vue ^6.0.8`, `pinia ^4.0.3`, `vue-router ^5.3.1`, `vitest ^4.1.11`, `@vue/test-utils ^2.5.0`, `jsdom ^30.0.1`, `@playwright/test ^1.63.0`, `typescript ~6.0.0`, `vue-tsc ^3.3.11`, `eslint ^10.10.0`, `eslint-plugin-vue ~10.11.0`, `@vue/eslint-config-typescript ^14.9.0`, optional `oxlint ~1.82.0`, `prettier 3.9.6` or `oxfmt ^0.67.0`, `@tsconfig/node24`.

Node: Node 20 reached end of life on 2026-04-30; Node 24 is Active LTS until 2026-10-20 then maintenance until 2028-04-30; Node 26 becomes LTS on 2026-10-28. Latest tags: v24.22.0, v26.12.0, v22.23.3. Pin **Node 24** now (24.12+ satisfies create-vue and Vitest 5). [S58]

### 5.2 Breaking changes a scaffold must account for

- **Vite 8 is Rolldown-based**: "Vite 8 uses Rolldown and Oxc based tools instead of esbuild and Rollup"; `optimizeDeps.esbuildOptions` and the `esbuild` option are deprecated (auto-converted to `rolldownOptions` / `oxc`); default `build.target` moved to Baseline Widely Available as of 2026-01-01 (Chrome/Edge 111, Firefox 114, Safari 16.4). The `rolldown-vite` package is deprecated in favour of Vite 8. [S54][S51]
- **Vue 3.6 / Vapor mode is still a release candidate** (3.6.0-rc.1 on 2026-07-18, rc.11 on 2026-10-10, with many Vapor compiler fixes still landing). Vapor mode is "100% opt-in" per component via `<script setup vapor>`. Scaffold on Vue 3.5 and do not use Vapor in phase 1; the upgrade to 3.6 should not require code changes for non-Vapor components (UNVERIFIED until 3.6.0 final). [S55]
- **Pinia 4, Vue Router 5, Vitest 5** are all new majors in 2026; their migration notes were not read here (UNVERIFIED details). Following create-vue's pins (Pinia 4, Router 5, Vitest 4.1) is the low-risk path. [S52]

### 5.3 TypeScript 7 trap

- `typescript@latest` is 7.0.2, the native (Go) compiler: the npm package ships platform binaries and has **no `main` entry (no JavaScript API)**. A separate `@typescript/typescript6` package (6.0.2) exists for tools that need the old API. [S51]
- typescript-eslint 8.71.2 declares `typescript <6.1.0`; vue-tsc depends on the TypeScript JS API through `@volar/typescript`. create-vue pins `typescript ~6.0.0`. [S51][S52] The Vue language tools moved their own build to TS 7 with `@typescript/typescript6` support in July 2026, but whether `vue-tsc` type-checks a project whose `typescript` dependency is 7.x: UNVERIFIED. [S56]
- Action: pin `"typescript": "~6.0.3"` in `ui/package.json` and tell agents not to run `npm i typescript@latest`.

### 5.4 Graph visualisation

| Option | Version | Licence | Fit for an Apache-2.0 app showing up to 2,000 nodes |
|---|---|---|---|
| Cytoscape.js | 3.34.4 (2026-10-15) | MIT, zero runtime dependencies, ships its own types | Strong: mature graph model, selectors, styling, compound nodes, many layouts; canvas renderer plus an opt-in WebGL mode (`webgl: false` by default in renderer options) [S59][S51] |
| sigma.js + graphology | sigma 4.0.3 (2026-10-15), graphology 0.26.0 (2025-01-26) | MIT | WebGL, built for much larger graphs; sigma 4.0.0 was released 2026-10-08 with three patch releases in a week, so v4 is very fresh (3.0.3 is the last v3) [S51] |
| Neo4j NVL (`@neo4j-nvl/base`) | 2.0.0 (2026-09-15) | **Proprietary** | Not usable: licence says NVL "may only be used with (i) the Aura software as a service offering ... or (ii) the proprietary commercial graph database products developed by Neo4j ... subject to the Neo4j Subscription Agreement" [S53] |

- **Recommendation: Cytoscape.js 3.34.x** (already the plan's choice). Layout add-ons: `cytoscape-fcose` 2.2.0 (MIT, last release 2023) and `cytoscape-dagre` 4.0.1 (MIT, 2026-08-28) for hierarchies such as ownership trees; avoid `cytoscape-elk` unless the team accepts `elkjs` under EPL-2.0 OR GPL-3.0-or-later. `@types/cytoscape` is a deprecated stub (types are bundled). [S51]
- Keep sigma.js as the fallback if a "whole network" view beyond about 10,000 elements becomes a requirement (threshold is a rule of thumb, not measured here).

---

## 6. Local LLM for the copilot (short)

- **Ollama v0.40.5** is the latest release tag (2026-10-15); MIT licence; official Docker image `ollama/ollama`; official Python client `ollama` 0.6.3 (2026-09-29, depends on `httpx>=0.27` and `pydantic>=2.9`). [S60][S39]
- **neo4j-graphrag 1.22.0** (2026-10-01), Apache-2.0, Python `>=3.10,<3.15`, requires `neo4j>=6.3.1,<7`. Retrievers: `VectorRetriever`, `VectorCypherRetriever`, `HybridRetriever`, `HybridCypherRetriever`, `Text2CypherRetriever`, `ToolsRetriever` (plus external Pinecone/Weaviate/Qdrant retrievers). LLM adapters include `OllamaLLM` (extra `ollama`), OpenAI, Anthropic, Mistral, Cohere, Vertex AI, Bedrock, Google GenAI. [S36]
  - `Text2CypherRetriever(driver, llm, neo4j_schema=None, examples=None, result_formatter=None, custom_prompt=None, neo4j_database=None)`. In 1.22.0 it runs `EXPLAIN` on the generated query and refuses anything whose `query_type` is not read-only (`"r"`), and executes with `RoutingControl.READ`. Schema extraction uses APOC (`apoc.meta.data`), so APOC Core must be installed. It also uses the new `SEARCH` clause for vector queries when available. Verified in the 1.22.0 wheel. [S36]
- Community Edition has no role-based access control (Enterprise only), so a "read-only database user" cannot be created; rely on the EXPLAIN query-type check, read transactions, procedure allowlists and the template-first design the plan already proposes. [S10]
- Neo4j text-to-Cypher resources:
  - neo4j-labs/text2cypher (CC0-1.0, Labs project, last commit 2026-10-09): synthetic question/Cypher datasets generated with GPT-4o, GPT-4 Turbo, Gemini and Claude Opus over demo databases, evaluation notebooks, fine-tuning notebooks (CodeLlama 13B, StarCoder2 3B, Llama 3, Codestral). [S61]
  - Neo4j's Hugging Face organisation (https://huggingface.co/neo4j/models), the "fine-tuned Neo4j Text2Cypher (2024) model" blog post and the "Text2Cypher: Bridging Natural Language and Graph Databases" paper (arXiv 2412.10064) exist per search results; the model referred to as `neo4j/text2cypher-gemma-2-9b-it-finetuned-2024v1` is 9B (above the 8B budget). Dataset and model cards could not be opened (huggingface.co blocked): details UNVERIFIED. [S62]
- Best 8B-or-smaller open-weight model for text-to-Cypher in 2026: UNVERIFIED. No Neo4j or neutral benchmark page could be read today. Treat model choice as an experiment: evaluate two or three Ollama-available models in the 3B to 8B range against the copilot's 10 benchmark questions plus a slice of the Neo4j text2cypher data, with the real schema in the prompt.
- Memory reality: on CPU-only laptops an 8B model in 4-bit quantisation needs roughly 5 to 6 GB of RAM and a 3B model roughly 2 to 3 GB (typical GGUF sizes; UNVERIFIED for any specific model since ollama.com was blocked). Combined with Neo4j this is the main constraint on 8 GB machines (section 8).

---

## 7. Dev environment and CI

### 7.1 Devcontainer

- `devcontainer.json` reference properties include `image`/`build`, `dockerComposeFile` + `service` + `runServices`, `features`, `forwardPorts`, `portsAttributes`, `postCreateCommand`/`postStartCommand`, `remoteUser`, `customizations`, `mounts`, `runArgs`; Codespaces honours `hostRequirements` (`cpus`, `memory`, `storage`) to hide machine types below the requirement. [S63][S66]
- Current official features (devcontainers/features, `main`) [S64]:
  - `ghcr.io/devcontainers/features/python` 1.8.0: default `version: os-provided`; default `installTools: true` installs flake8, black, yapf, mypy, pylint and others; "May require source code compilation". Prefer uv-managed Python instead.
  - `ghcr.io/devcontainers/features/node` 2.1.1: default `version: lts`.
  - `ghcr.io/devcontainers/features/docker-in-docker` 4.1.3: privileged, own `/var/lib/docker` volume, installs Compose.
  - `ghcr.io/devcontainers/features/docker-outside-of-docker` 1.10.1: reuses the host Docker socket.
- Suggested shape (sketch): a Compose-based devcontainer where `dev` runs next to the same `neo4j` service users run locally, so nobody needs Docker-in-Docker just to reach Neo4j; add the docker-in-docker feature only if Testcontainers must run inside the devcontainer.

```jsonc
// .devcontainer/devcontainer.json (sketch)
{
  "name": "neonradar",
  "dockerComposeFile": ["../compose.yaml", "compose.dev.yaml"],
  "service": "dev",                       // built FROM ghcr.io/astral-sh/uv:python3.14-trixie
  "runServices": ["dev", "neo4j"],
  "workspaceFolder": "/workspaces/neonradar",
  "features": { "ghcr.io/devcontainers/features/node:2": { "version": "24" } },
  "hostRequirements": { "cpus": 4, "memory": "16gb" },
  "forwardPorts": [7474, 7687, 8000, 5173],
  "postCreateCommand": "uv sync --locked && npm ci --prefix ui"
}
```

  The `dev` image needs `pkg-config libicu-dev build-essential` for PyICU (section 3.5).

### 7.2 GitHub Codespaces quota and machine sizes

- Included usage per month: GitHub Free personal account 120 core hours and 15 GB storage; Pro 180 core hours and 20 GB. Organisation plans include none. [S65]
- Compute is billed per core: 2-core x2, 4-core x4, 8-core x8, 16-core x16, 32-core x32 (USD 0.18 to 2.88 per hour). So 120 core hours = 60 hours on a 2-core or 30 hours on a 4-core machine per month. [S66]
- Machine types range from "2 cores, 8 GB RAM, and 32 GB storage, up to 32 cores, 128 GB RAM, and 128 GB storage"; 2-core and 4-core types have 32 GB storage. The per-type RAM for 4/8/16-core was not listed in the pages read (4-core = 16 GB is common knowledge but UNVERIFIED here). [S66]
- "Free use of GitHub Codespaces is included in personal accounts only." Organisations on the Free plan cannot pay for Codespaces, so for a repository in a free organisation each intern's own quota pays. Team/Enterprise organisations can choose organisation-owned (organisation-paid) codespaces. [S66]
- Implication: Codespaces covers the small-dataset mode well; the full 500k/2M benchmark plus GDS plus a local LLM will not fit in a 2-core 8 GB codespace and burns the free quota quickly on 4-core.

### 7.3 GitHub Actions versions (latest release tags, checked with git) [S67]

| Action | Latest | Notes |
|---|---|---|
| actions/checkout | v7.0.1 (2026-07-17), major tag `v7` | v7 refuses fork PR code by default under `pull_request_target`/`workflow_run`; node24 since v5 (runner >= v2.327.1) |
| actions/setup-python | v7.0.0 (2026-07-19), `v7` | v7: ESM internals, no input changes; node24 since v6 |
| astral-sh/setup-uv | v10.3.0 (2026-10-09) | **no moving major tag after `v7`**; pin the full version or a commit SHA (the uv docs and README pin by SHA) |
| actions/setup-node | v7.1.0 (2026-10-07), `v7` | v7 removed the dummy `NODE_AUTH_TOKEN` fallback |
| actions/cache | v6.1.0, `v6` | |
| github/codeql-action | v4.39.0 (2026-10-15), `v4` | |
| googleapis/release-please-action | v5.0.0 (2026-04-22), `v5` | v5 breaking change: node24 runtime |
| gitleaks/gitleaks-action | v3.0.0, `v3` | needs a free `GITLEAKS_LICENSE` for organisation-owned repos |
| pre-commit/action | v3.0.1 | |

- Node 20 deprecation on hosted runners (default switched to Node 24 on 2026-06-02, Node 20 removed 2026-09-16) is stated in the gitleaks-action README; not confirmed on a GitHub page today (UNVERIFIED from GitHub directly). Either way, use the node24 majors above. [S67]
- Public repositories: Actions minutes are free on standard GitHub-hosted runners, and the standard Linux runner for public repos has 4 vCPU and 16 GB RAM (private repos: 2 vCPU, 8 GB). Service containers require Linux runners. [S79][S69]

Neo4j as a service container (pattern from the GitHub service-container docs, with the Neo4j docs' wget healthcheck) [S68][S15]:

```yaml
jobs:
  test:
    runs-on: ubuntu-24.04
    services:
      neo4j:
        image: neo4j:2026.09.0-community
        env:
          NEO4J_AUTH: neo4j/ci-password-123
          NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
        ports: ["7687:7687", "7474:7474"]
        options: >-
          --health-cmd "wget --no-verbose --tries=1 --spider localhost:7474 || exit 1"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 30
          --health-start-period 60s
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10.3.0
      - run: uv sync --locked
      - run: uv run pytest
        env:
          NEO4J_URI: neo4j://localhost:7687
          NEO4J_PASSWORD: ci-password-123
```

Alternative: Testcontainers inside pytest (Docker is available on Ubuntu runners), which keeps CI and local tests identical.

### 7.4 Secret scanning and gitleaks

- Secret scanning alerts, push protection, code scanning and the CodeQL CLI are "Available for public repositories by default" (free). [S70]
- Push protection for users is enabled by default for every account and blocks pushes of supported secrets to public repositories; repository-level push protection is disabled by default and must be switched on by an admin (it generates bypass alerts). [S70]
- gitleaks v8.30.1 (2026-03-12), MIT; run it as a pre-commit hook (`id: gitleaks`) and, for organisation-owned repos, prefer the CLI or GitHub's own secret scanning over gitleaks-action (licence key needed). [S67][S78]

### 7.5 Dependabot

- Supported `package-ecosystem` values include `uv` (docs list "v0.11"), `pip`, `npm` (also pnpm/yarn), `github-actions`, `docker`, `docker-compose`, `devcontainers` and `pre-commit`; all available on github.com. [S71]
- Version updates now have a default 3-day cooldown even without a `cooldown` block (security updates excluded). [S71]

```yaml
version: 2
updates:
  - { package-ecosystem: uv, directory: "/", schedule: { interval: weekly },
      groups: { python: { update-types: [minor, patch] } } }
  - { package-ecosystem: npm, directory: "/ui", schedule: { interval: weekly } }
  - { package-ecosystem: github-actions, directory: "/", schedule: { interval: weekly } }
  - { package-ecosystem: pre-commit, directory: "/", schedule: { interval: weekly } }
  - { package-ecosystem: devcontainers, directory: "/", schedule: { interval: weekly } }
  - package-ecosystem: docker-compose
    directory: "/"
    schedule: { interval: weekly }
    ignore:
      - dependency-name: "neo4j"   # Neo4j moves to new tags monthly; bump by hand (LTS, GDS pairing)
```

### 7.6 CodeQL default setup

- Default setup is GitHub's recommended starting point: it builds the configuration automatically, picks up newly added CodeQL languages, and needs no workflow file; it requires Actions to be enabled. CodeQL languages include Python, JavaScript/TypeScript and GitHub Actions workflows. [S72]

### 7.7 Conventional Commits and release-please

- Conventional Commits current version: 1.0.0. [S73]
- release-please (library 17.11.2 on npm) supports release types including `python` (pyproject.toml), `node` and `simple`; a monorepo with a Python workspace and a Vue app should use manifest mode (`release-please-config.json` + `.release-please-manifest.json`). The action's README examples still show `@v4` although `v5` is current. [S74]

---

## 8. Docker Compose and memory

### 8.1 Compose specification notes

- "The top-level `version` property is ... only informative and you'll receive a warning message that it is obsolete if used. Compose always uses the most recent schema." Use the top-level `name:` instead. [S75]
- Healthcheck fields: `test` (`CMD`, `CMD-SHELL`, `NONE`), `interval`, `timeout`, `retries`, `start_period`, `start_interval` (Compose 2.20.2+); `disable: true` turns off an image healthcheck. `mem_limit` is supported. [S75]
- Docker Compose v5 is current: latest tag v5.6.0 (2026-10-02); v5.0.0 was tagged 2025-12-02; the Go module path is `github.com/docker/compose/v5`. What changed in v5 (breaking changes, removed features): UNVERIFIED (release notes live only on the GitHub releases page, which could not be read). [S76]

### 8.2 Neo4j healthcheck

- Neo4j's own Compose example: `test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider localhost:7474 || exit 1"]`. `wget` is present in the image, `curl` is not. [S15][S3]
- This only proves the HTTP connector is up. A stricter check is `cypher-shell -u neo4j -p "$PASS" "RETURN 1"` (cypher-shell ships in the image), at the cost of starting a JVM on every probe; in the application, call `driver.verify_connectivity()` with retries at startup. [S9]
- Give a generous `start_period` (60 s or more) on first start because the GDS jar is downloaded then.

Reference service (assembled from the verified pieces above):

```yaml
name: neonradar
services:
  neo4j:
    image: neo4j:2026.09.0-community
    ports: ["7474:7474", "7687:7687"]
    environment:
      NEO4J_AUTH_FILE: /run/secrets/neo4j_auth          # file contains neo4j/<password, 8+ chars>
      NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
      NEO4J_dbms_security_procedures_unrestricted: "apoc.*,gds.*"   # keeps GDS working when offline
      NEO4J_db_query_default__language: CYPHER_25
      NEO4J_server_memory_heap_initial__size: ${NEO4J_HEAP:-2G}
      NEO4J_server_memory_heap_max__size: ${NEO4J_HEAP:-2G}
      NEO4J_server_memory_pagecache_size: ${NEO4J_PAGECACHE:-1G}
      NEO4J_server_jvm_additional: -XX:+ExitOnOutOfMemoryError
    volumes:
      - neo4j-data:/data
      - neo4j-plugins:/plugins      # persists the downloaded GDS jar
      - ./data/import:/import
    mem_limit: ${NEO4J_MEM_LIMIT:-4g}
    secrets: [neo4j_auth]
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider localhost:7474 || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 30
      start_period: 90s
secrets:
  neo4j_auth:
    file: ./secrets/neo4j_auth.txt
volumes:
  neo4j-data:
  neo4j-plugins:
```

### 8.3 Memory realities

Facts:
- Neo4j's hardware guideline for personal use and development: "2GB minimum, 16GB or more recommended". [S12]
- Docker Desktop's VM "Defaults to 50% of your host's memory" (Mac, Linux, Windows Hyper-V); so 8 GB on a 16 GB laptop and 4 GB on an 8 GB laptop unless changed. Windows WSL2 memory limits are governed by WSL, not checked here (UNVERIFIED). [S77]
- The image defaults page cache to 512M; heap is whatever you set (set it). [S4]
- GDS needs heap for projections and algorithms and is capped at 4 cores on CE. [S25][S26]

Sizing guidance (engineering estimates, not measured on the target data):

| | 16 GB laptop | 8 GB laptop |
|---|---|---|
| Docker VM / budget for containers | raise Docker Desktop to about 10 GB if Ollama also runs in Docker; otherwise the default 8 GB is enough for Neo4j | default 4 GB |
| Neo4j heap (initial = max) | 3 to 4 GB | 1 GB |
| Neo4j page cache | 2 GB (the 500k-node / 2M-relationship store should mostly fit; verify with the actual store size) | 512 MB |
| Container `mem_limit` | about 6 to 7 GB | about 2 to 2.5 GB |
| GDS | fine for the full benchmark graph; run `gds.graph.project.estimate` first | small-dataset mode (about 10k nodes) only |
| Local LLM | 7B/8B 4-bit model, preferably run natively (Metal on Apple Silicon) rather than inside the Docker VM; expect contention with IDE + browser | at most a 1B to 3B model, or template-only copilot; or use a Codespace (CPU-only, slow) |
| Verdict | full stack workable with discipline | Neo4j + UI + small data works; full data + GDS + LLM at once does not |

The plan's target (load 500k nodes / 2M relationships in under 10 minutes on a 16 GB laptop) is realistic only with `neo4j-admin database import full` for the initial load (minutes) rather than transactional UNWIND batches (likely much slower); this is an expectation, not a measurement.

---

## Pinned versions table

| Component | Recommended version or range | Reason | Source URL |
|---|---|---|---|
| Neo4j Community (Docker) | `neo4j:2026.09.0-community` (exact); move to the 2026 LTS tag when published | current release line; Cypher 25 features (ACYCLIC 2026.03, SEARCH full-text 2026.09); matches GDS 2026.09 | https://github.com/docker-library/official-images/blob/master/library/neo4j |
| Neo4j (conservative alternative) | `neo4j:5.26.32-community` | only LTS available today, but Cypher 5 frozen and GDS 2.13 | https://github.com/docker-library/official-images/blob/master/library/neo4j |
| GDS plugin | 2026.09 (via `NEO4J_PLUGINS`, persisted in `/plugins`) | must match the Neo4j version; CE limited to 4 cores, 3 models | https://github.com/neo4j/graph-data-science/blob/2026.09.0/doc/modules/ROOT/pages/installation/supported-neo4j-versions.adoc |
| APOC Core | bundled with the image (2026.09) | ships in `/var/lib/neo4j/labs`, works offline, Apache-2.0 | https://github.com/neo4j/docker-neo4j/blob/master/docker-image-src/calver/coredb/neo4j-plugins.json |
| Python | 3.14 (3.14.8), `>=3.14,<3.15` | 3.15 too new for duckdb/graphrag/GDS client; 3.13 now security-only | https://peps.python.org/pep-0745/ |
| neo4j (driver) | `>=6.4,<7` | current major; supports 4.4 to 2026.x servers; required by graphrag (>=6.3.1) and testcontainers (>=6) | https://pypi.org/project/neo4j/ |
| neo4j-rust-ext | `==6.4.1.*` (optional) | same API, faster; must match driver version | https://pypi.org/project/neo4j-rust-ext/ |
| graphdatascience | `>=2.2,<2.4` | supports GDS 2.13 and 2026.09; V2 snake_case API | https://github.com/neo4j/graph-data-science-client/blob/main/doc/modules/ROOT/pages/installation.adoc |
| neo4j-graphrag | `>=1.22,<2` with `[ollama]` | Text2CypherRetriever with read-only EXPLAIN guard; OllamaLLM | https://pypi.org/project/neo4j-graphrag/ |
| uv | `0.13.x` (0.13.1); `uv_build>=0.13.1,<0.14` | workspaces, lockfile, Python management | https://pypi.org/project/uv/ |
| ruff | `0.17.x` (pre-commit rev v0.17.1) | lint + format | https://pypi.org/project/ruff/ |
| mypy | `>=2.4,<3` | strict CI type checking | https://pypi.org/project/mypy/ |
| pytest | `>=9.1,<10` | test runner | https://pypi.org/project/pytest/ |
| pydantic | `>=2.14,<3` | schema and validation (replaces EE-only DB constraints) | https://pypi.org/project/pydantic/ |
| FastAPI | `>=0.143,<0.144` (pin minor; 0.x) | API layer | https://pypi.org/project/fastapi/ |
| typer | `>=0.27,<0.28` | CLI | https://pypi.org/project/typer/ |
| httpx | `>=0.28,<0.29` (transitive) | used by ollama client and FastAPI test tooling; upstream slow, watch httpx2 | https://pypi.org/project/httpx/ |
| duckdb | `>=1.5,<2` | Splink backend; 2.0 only in dev builds | https://pypi.org/project/duckdb/ |
| pyarrow | `>=26,<27` | Splink dependency, Arrow tables | https://pypi.org/project/pyarrow/ |
| polars (optional) | `>=1.44,<2` | avoid a ten-day-old major in phase 1 | https://pypi.org/project/polars/ |
| testcontainers | `[neo4j]>=4.15,<5` | import from `testcontainers.community.neo4j` | https://pypi.org/project/testcontainers/ |
| pre-commit | `>=4.7,<5` | hooks (needs Python 3.11+) | https://pypi.org/project/pre-commit/ |
| splink | `==5.0.*` | current major (2026-09-28); smaller install; v4 syntax no longer valid | https://github.com/moj-analytical-services/splink/blob/master/CHANGELOG.md |
| rigour | `>=2.5,<3` | name analysis/comparison; replaces unmaintained fingerprints | https://pypi.org/project/rigour/ |
| normality | `>=3.1,<4` | ICU transliteration for Arabic/Cyrillic; needs PyICU | https://pypi.org/project/normality/ |
| PyICU | `>=2.16,<3` (built from source with libicu-dev) | ICU transforms; no wheels on PyPI | https://pypi.org/project/PyICU/ |
| anyascii | `>=0.3.3` | ISC fallback transliteration (instead of GPL unidecode) | https://pypi.org/project/anyascii/ |
| rapidfuzz | `>=3.14,<4` | fast fuzzy scoring, MIT | https://pypi.org/project/rapidfuzz/ |
| jellyfish | `>=1.2,<2` | phonetic keys, MIT | https://pypi.org/project/jellyfish/ |
| Node.js | 24 LTS (24.12+; latest 24.22.0) | Node 20 EOL; create-vue and Vitest 5 need 22.12+/24 | https://github.com/nodejs/Release/blob/main/schedule.json |
| vue | `^3.5.44` | 3.6 (Vapor) still RC | https://www.npmjs.com/package/vue |
| vite | `^8.3.4` | Rolldown/Oxc-based current major | https://www.npmjs.com/package/vite |
| @vitejs/plugin-vue | `^6.0.10` | Vite 8 support | https://www.npmjs.com/package/@vitejs/plugin-vue |
| typescript | `~6.0.3` | TS 7 has no JS API; vue-tsc and typescript-eslint need 6.x | https://www.npmjs.com/package/typescript |
| vue-tsc | `^3.3.13` | SFC type checking | https://www.npmjs.com/package/vue-tsc |
| pinia | `^4.1.0` | matches create-vue 3.24 | https://www.npmjs.com/package/pinia |
| vue-router | `^5.4.0` | matches create-vue 3.24 | https://www.npmjs.com/package/vue-router |
| vitest | `^4.1.12` (or `^5.0.5` deliberately) | create-vue still pins 4.1; v5 is six weeks old | https://www.npmjs.com/package/vitest |
| @playwright/test | `^1.64.1` | e2e tests | https://www.npmjs.com/package/@playwright/test |
| cytoscape | `^3.34.4` | MIT, zero deps, right size for up to 2,000 nodes | https://www.npmjs.com/package/cytoscape |
| cytoscape-fcose / cytoscape-dagre | `^2.2.0` / `^4.0.1` | MIT layouts | https://www.npmjs.com/package/cytoscape-dagre |
| @neo4j-nvl/base | do not use | proprietary, Aura/Enterprise only | https://registry.npmjs.org/@neo4j-nvl/base/-/base-2.0.0.tgz |
| Ollama | v0.40.x (v0.40.5) | offline model runtime, MIT | https://github.com/ollama/ollama |
| ollama (Python client) | `>=0.6.3,<0.7` | used by OllamaLLM | https://pypi.org/project/ollama/ |
| actions/checkout | `v7` (7.0.1) or SHA | node24; safer fork handling | https://github.com/actions/checkout |
| actions/setup-python | `v7` (7.0.0) | node24 | https://github.com/actions/setup-python |
| astral-sh/setup-uv | `v10.3.0` exact or SHA | no floating major tag | https://github.com/astral-sh/setup-uv |
| actions/setup-node | `v7` (7.1.0) | node24 | https://github.com/actions/setup-node |
| github/codeql-action | `v4` (4.39.0), or default setup | free on public repos | https://github.com/github/codeql-action |
| googleapis/release-please-action | `v5` (5.0.0) | node24 | https://github.com/googleapis/release-please-action |
| gitleaks | v8.30.1 (pre-commit hook) | secret scanning before push | https://github.com/gitleaks/gitleaks |
| devcontainer features | `ghcr.io/devcontainers/features/node:2` (2.1.1); `docker-in-docker:4` (4.1.3) only if Testcontainers must run inside the devcontainer | use uv-managed Python rather than the python feature (which may compile Python from source) | https://github.com/devcontainers/features |
| Docker Compose | v5.x (5.6.0); no `version:` key | current major | https://docs.docker.com/reference/compose-file/version-and-name/ |

---

## Sources

All checked 2026-10-16 unless noted. "Rendered at" gives the public page built from the verified source file.

- [S1] Docker official-images manifest for neo4j: https://github.com/docker-library/official-images/blob/master/library/neo4j (read via https://raw.githubusercontent.com/docker-library/official-images/master/library/neo4j). Checked 2026-10-16.
- [S2] neo4j/neo4j release tags (git ls-remote; tag commit dates from shallow fetch): https://github.com/neo4j/neo4j/tags. Checked 2026-10-16.
- [S3] Published Dockerfiles: https://github.com/neo4j/docker-neo4j-publish/blob/32e4b7cfe361a4d8a6debf7bc1a6ed8d71507356/2026.09.0/trixie/community/Dockerfile and https://github.com/neo4j/docker-neo4j-publish/blob/3abe11cd8b22f68279adf33ba879c73e10581802/5.26.32/trixie/community/Dockerfile. Checked 2026-10-16.
- [S4] docker-neo4j entrypoint and plugin manifest (commit fd9e4ec, 2026-09-30): https://github.com/neo4j/docker-neo4j/blob/master/docker-image-src/calver/coredb/docker-entrypoint.sh and https://github.com/neo4j/docker-neo4j/blob/master/docker-image-src/calver/coredb/neo4j-plugins.json. Checked 2026-10-16.
- [S5] docker-neo4j bundled-plugin test: https://github.com/neo4j/docker-neo4j/blob/master/src/test/java/com/neo4j/docker/coredb/plugins/TestBundledPluginInstallation.java. Checked 2026-10-16.
- [S6] Cypher manual, Select Cypher version: https://github.com/neo4j/docs-cypher/blob/dev/modules/ROOT/pages/queries/select-version.adoc (commit 332ce05, 2026-10-15); rendered at https://neo4j.com/docs/cypher-manual/25/queries/select-version/. Checked 2026-10-16.
- [S7] Operations Manual, Docker plugins: https://github.com/neo4j/docs-operations/blob/dev/modules/ROOT/pages/docker/plugins.adoc (commit 8b6a119, 2026-10-15); rendered at https://neo4j.com/docs/operations-manual/current/docker/plugins/. Checked 2026-10-16.
- [S8] Operations Manual, Docker configuration: https://github.com/neo4j/docs-operations/blob/dev/modules/ROOT/pages/docker/configuration.adoc; rendered at https://neo4j.com/docs/operations-manual/current/docker/configuration/. Checked 2026-10-16.
- [S9] Operations Manual, Docker operations (import, memory recommendation, cypher-shell): https://github.com/neo4j/docs-operations/blob/dev/modules/ROOT/pages/docker/operations.adoc; rendered at https://neo4j.com/docs/operations-manual/current/docker/operations/. Checked 2026-10-16.
- [S10] Operations Manual, edition comparison table: https://github.com/neo4j/docs-operations/blob/dev/modules/ROOT/pages/introduction.adoc; rendered at https://neo4j.com/docs/operations-manual/current/introduction/. Checked 2026-10-16.
- [S11] Operations Manual, memory configuration and vector index memory: https://github.com/neo4j/docs-operations/blob/dev/modules/ROOT/pages/performance/memory-configuration.adoc and .../performance/vector-index-memory-configuration.adoc; rendered at https://neo4j.com/docs/operations-manual/current/performance/memory-configuration/. Checked 2026-10-16.
- [S12] Operations Manual, system requirements: https://github.com/neo4j/docs-operations/blob/dev/modules/ROOT/pages/installation/requirements.adoc; rendered at https://neo4j.com/docs/operations-manual/current/installation/requirements/. Checked 2026-10-16.
- [S13] Operations Manual, breaking changes and deprecations (LTS policy, "next LTS release in 2026"): https://github.com/neo4j/docs-operations/blob/dev/modules/ROOT/pages/breaking-changes.adoc and .../deprecations.adoc; rendered at https://neo4j.com/docs/operations-manual/current/deprecations/. Checked 2026-10-16.
- [S14] Operations Manual, full import: https://github.com/neo4j/docs-operations/blob/dev/modules/ROOT/pages/import/full-import.adoc; rendered at https://neo4j.com/docs/operations-manual/current/import/full-import/. Checked 2026-10-16.
- [S15] Operations Manual, clustering tutorial with Compose healthcheck: https://github.com/neo4j/docs-operations/blob/dev/modules/ROOT/pages/tutorial/tutorial-clustering-docker.adoc; rendered at https://neo4j.com/docs/operations-manual/current/tutorial/tutorial-clustering-docker/. Checked 2026-10-16.
- [S16] Operations Manual, Compose standalone and Docker secrets: https://github.com/neo4j/docs-operations/blob/dev/modules/ROOT/pages/docker/docker-compose-standalone.adoc; rendered at https://neo4j.com/docs/operations-manual/current/docker/docker-compose-standalone/. Checked 2026-10-16.
- [S17] Cypher manual, create constraints: https://github.com/neo4j/docs-cypher/blob/dev/modules/ROOT/pages/schema/constraints/create-constraints.adoc; rendered at https://neo4j.com/docs/cypher-manual/25/schema/constraints/create-constraints/. Checked 2026-10-16.
- [S18] Cypher manual, full-text indexes: https://github.com/neo4j/docs-cypher/blob/dev/modules/ROOT/pages/indexes/search-indexes/full-text-indexes.adoc; rendered at https://neo4j.com/docs/cypher-manual/25/indexes/search-indexes/full-text-indexes/. Checked 2026-10-16.
- [S19] Cypher manual, vector indexes: https://github.com/neo4j/docs-cypher/blob/dev/modules/ROOT/pages/indexes/search-indexes/vector-indexes.adoc; rendered at https://neo4j.com/docs/cypher-manual/25/indexes/search-indexes/vector-indexes/. Checked 2026-10-16.
- [S20] Cypher manual, SEARCH clause: https://github.com/neo4j/docs-cypher/blob/dev/modules/ROOT/pages/clauses/search.adoc; rendered at https://neo4j.com/docs/cypher-manual/25/clauses/search/. Checked 2026-10-16.
- [S21] Cypher manual, variable-length paths (QPP): https://github.com/neo4j/docs-cypher/blob/dev/modules/ROOT/pages/patterns/variable-length-paths.adoc; rendered at https://neo4j.com/docs/cypher-manual/25/patterns/variable-length-paths/. Checked 2026-10-16.
- [S22] Cypher manual, match modes and path modes; acyclic paths: https://github.com/neo4j/docs-cypher/blob/dev/modules/ROOT/pages/patterns/reference/match-modes-and-path-modes.adoc and .../patterns/acyclic-paths.adoc. Checked 2026-10-16.
- [S23] Cypher manual, additions, deprecations, removals: https://github.com/neo4j/docs-cypher/blob/dev/modules/ROOT/pages/deprecations-additions-removals-compatibility.adoc; rendered at https://neo4j.com/docs/cypher-manual/25/deprecations-additions-removals-compatibility/. Checked 2026-10-16.
- [S24] GDS supported Neo4j versions (tag 2026.09.0): https://github.com/neo4j/graph-data-science/blob/2026.09.0/doc/modules/ROOT/pages/installation/supported-neo4j-versions.adoc; rendered at https://neo4j.com/docs/graph-data-science/current/installation/supported-neo4j-versions/. Checked 2026-10-16.
- [S25] GDS editions: https://github.com/neo4j/graph-data-science/blob/2026.09.0/doc/modules/ROOT/partials/introduction/enterprise-features.adoc; rendered at https://neo4j.com/docs/graph-data-science/current/introduction/. Checked 2026-10-16.
- [S26] GDS system requirements and memory estimation: https://github.com/neo4j/graph-data-science/blob/2026.09.0/doc/modules/ROOT/pages/installation/System-requirements.adoc and .../common-usage/memory-estimation.adoc. Checked 2026-10-16.
- [S27] GDS Docker installation: https://github.com/neo4j/graph-data-science/blob/2026.09.0/doc/modules/ROOT/pages/installation/installation-docker.adoc. Checked 2026-10-16.
- [S28] GDS README, LICENSE.txt and build toolchain at tag 2026.09.0: https://github.com/neo4j/graph-data-science/blob/2026.09.0/README.adoc, https://github.com/neo4j/graph-data-science/blob/2026.09.0/LICENSE.txt, https://github.com/neo4j/graph-data-science/blob/2026.09.0/build-logic/src/main/groovy/buildlogic-gds-java-plain.gradle. Checked 2026-10-16.
- [S29] GDS release tags (git ls-remote; dates from shallow fetch): https://github.com/neo4j/graph-data-science/tags. Checked 2026-10-16.
- [S30] Neo4j Community licence and README at tag 2026.09.0: https://github.com/neo4j/neo4j/blob/2026.09.0/LICENSE.txt and https://github.com/neo4j/neo4j/blob/2026.09.0/README.asciidoc. Checked 2026-10-16.
- [S31] APOC licence: https://github.com/neo4j/apoc/blob/dev/LICENSE (commit 4288f52, 2026-10-15). Checked 2026-10-16.
- [S32] PyPI neo4j and neo4j-driver: https://pypi.org/project/neo4j/ and https://pypi.org/project/neo4j-driver/ (JSON API). Checked 2026-10-16.
- [S33] Python driver README and CHANGELOG (branch 6.x, commit 9755761, 2026-10-15): https://github.com/neo4j/neo4j-python-driver/blob/6.x/README.rst and https://github.com/neo4j/neo4j-python-driver/blob/6.x/CHANGELOG.md. Checked 2026-10-16.
- [S34] Python driver manual sources (install, query-simple, transactions, performance; commit 8574f12, 2026-10-13): https://github.com/neo4j/docs-drivers/tree/dev/python-manual/modules/ROOT/pages; rendered at https://neo4j.com/docs/python-manual/current/. Checked 2026-10-16.
- [S35] graphdatascience client: https://pypi.org/project/graphdatascience/; installation and migration docs https://github.com/neo4j/graph-data-science-client/blob/main/doc/modules/ROOT/pages/installation.adoc and .../migration-from-1x.adoc; rendered at https://neo4j.com/docs/graph-data-science-client/current/. Checked 2026-10-16.
- [S36] neo4j-graphrag 1.22.0 (PyPI metadata and wheel inspected) and repository: https://pypi.org/project/neo4j-graphrag/ and https://github.com/neo4j/neo4j-graphrag-python. Checked 2026-10-16.
- [S37] PEP 790 (3.15), PEP 745 (3.14), PEP 719 (3.13) release schedules: https://peps.python.org/pep-0790/, https://peps.python.org/pep-0745/, https://peps.python.org/pep-0719/ (read from https://github.com/python/peps). Checked 2026-10-16.
- [S38] CPython release tags v3.15.0 (2026-10-09), v3.14.8 (2026-09-30), v3.13.16: https://github.com/python/cpython/tags. Checked 2026-10-16.
- [S39] PyPI JSON API for all other Python packages named in this report (versions, upload dates, licences, classifiers, wheel tags): https://pypi.org/project/<name>/ , e.g. https://pypi.org/project/uv/, https://pypi.org/project/splink/, https://pypi.org/project/rigour/, https://pypi.org/project/duckdb/. Checked 2026-10-16.
- [S40] uv workspaces docs at 0.13.1: https://github.com/astral-sh/uv/blob/0.13.1/docs/concepts/projects/workspaces.md; rendered at https://docs.astral.sh/uv/concepts/projects/workspaces/. Checked 2026-10-16.
- [S41] uv Docker and GitHub integration guides at 0.13.1: https://github.com/astral-sh/uv/blob/0.13.1/docs/guides/integration/docker.md and .../github.md; rendered at https://docs.astral.sh/uv/guides/integration/docker/. Checked 2026-10-16.
- [S42] testcontainers-python 4.15.0 wheel and repository (commit 6146aa1, 2026-10-07): https://pypi.org/project/testcontainers/ and https://github.com/testcontainers/testcontainers-python/tree/main/src/testcontainers/community/neo4j. Checked 2026-10-16.
- [S43] httpx2 project description: https://pypi.org/project/httpx2/ (repository https://github.com/pydantic/httpx2). Checked 2026-10-16.
- [S44] Splink changelog and 5.0 release post: https://github.com/moj-analytical-services/splink/blob/master/CHANGELOG.md and https://github.com/moj-analytical-services/splink/blob/master/docs/blog/posts/2026-09-28-splink-5-release.md. Checked 2026-10-16.
- [S45] Splink 5.0.0 wheel source (comparison_library.py, linker_components/evaluation.py, table_management.py, database_api.py): https://pypi.org/project/splink/5.0.0/. Checked 2026-10-16.
- [S45b] mypy changelog (2.0 section): https://github.com/python/mypy/blob/master/CHANGELOG.md. Checked 2026-10-16.
- [S46] Splink README quickstart: https://github.com/moj-analytical-services/splink/blob/master/README.md. Checked 2026-10-16.
- [S47] rigour 2.5.0 sdist and README: https://pypi.org/project/rigour/2.5.0/ and https://github.com/opensanctions/rigour (docs https://rigour.followthemoney.tech/). Checked 2026-10-16.
- [S48] normality 3.1.0 description: https://pypi.org/project/normality/. Checked 2026-10-16.
- [S49] fingerprints 1.3.1 description: https://pypi.org/project/fingerprints/. Checked 2026-10-16.
- [S50] PyICU 2.16.2 description and files: https://pypi.org/project/PyICU/. Checked 2026-10-16.
- [S51] npm registry metadata for vue, vite, typescript, @typescript/typescript6, pinia, vue-router, vitest, @playwright/test, create-vue, @vitejs/plugin-vue, vue-tsc, eslint, typescript-eslint, cytoscape, cytoscape-fcose, cytoscape-dagre, cytoscape-elk, elkjs, sigma, graphology, rolldown-vite: https://www.npmjs.com/package/<name> (JSON at https://registry.npmjs.org/<name>). Checked 2026-10-16.
- [S52] create-vue 3.24.0 package templates: https://registry.npmjs.org/create-vue/-/create-vue-3.24.0.tgz (source https://github.com/vuejs/create-vue). Checked 2026-10-16.
- [S53] NVL licence (LICENSE.txt inside the package): https://registry.npmjs.org/@neo4j-nvl/base/-/base-2.0.0.tgz. Checked 2026-10-16.
- [S54] Vite migration guide (v7 to v8): https://github.com/vitejs/vite/blob/main/docs/guide/migration.md; rendered at https://vite.dev/guide/migration. Checked 2026-10-16.
- [S55] Vue core changelog, `minor` branch (3.6 alpha to rc, Vapor notes): https://github.com/vuejs/core/blob/minor/CHANGELOG.md. Checked 2026-10-16.
- [S56] Vue language tools changelog: https://github.com/vuejs/language-tools/blob/master/CHANGELOG.md. Checked 2026-10-16.
- [S58] Node.js release schedule and tags: https://github.com/nodejs/Release/blob/main/schedule.json and https://github.com/nodejs/node/tags. Checked 2026-10-16.
- [S59] Cytoscape.js README and 3.34.4 package (renderer defaults include `webgl: false`): https://github.com/cytoscape/cytoscape.js and https://registry.npmjs.org/cytoscape/-/cytoscape-3.34.4.tgz. Checked 2026-10-16.
- [S60] Ollama tags, README and LICENSE at v0.40.5: https://github.com/ollama/ollama. Checked 2026-10-16.
- [S61] neo4j-labs/text2cypher (commit a8ed4d9, 2026-10-09): https://github.com/neo4j-labs/text2cypher. Checked 2026-10-16.
- [S62] Search-result pointers only (pages not readable): https://huggingface.co/neo4j/models, https://neo4j.com/blog/developer/fine-tuned-text2cypher-2024-model/, https://arxiv.org/html/2412.10064v1. Checked 2026-10-16.
- [S63] Dev container JSON reference: https://github.com/devcontainers/spec/blob/main/docs/specs/devcontainerjson-reference.md; rendered at https://containers.dev/implementors/json_reference/. Checked 2026-10-16.
- [S64] Dev container features (python 1.8.0, node 2.1.1, docker-in-docker 4.1.3, docker-outside-of-docker 1.10.1): https://github.com/devcontainers/features/tree/main/src. Checked 2026-10-16.
- [S65] GitHub docs, product usage included with each plan: https://github.com/github/docs/blob/main/content/billing/reference/product-usage-included.md (commit cb05161, 2026-10-15); rendered at https://docs.github.com/en/billing/reference/product-usage-included. Checked 2026-10-16.
- [S66] GitHub docs, Codespaces billing, machine types, hostRequirements and who pays: https://github.com/github/docs/blob/main/content/billing/concepts/product-billing/github-codespaces.md, .../content/codespaces/about-codespaces/what-are-codespaces.md, .../content/codespaces/troubleshooting/troubleshooting-included-usage.md, .../content/codespaces/managing-codespaces-for-your-organization/choosing-who-owns-and-pays-for-codespaces-in-your-organization.md, .../content/codespaces/setting-up-your-project-for-codespaces/configuring-dev-containers/setting-a-minimum-specification-for-codespace-machines.md. Checked 2026-10-16.
- [S67] GitHub Action release tags (git ls-remote, dates from shallow fetch) and READMEs/CHANGELOGs at those tags: https://github.com/actions/checkout, https://github.com/actions/setup-python, https://github.com/astral-sh/setup-uv, https://github.com/actions/setup-node, https://github.com/actions/cache, https://github.com/github/codeql-action, https://github.com/googleapis/release-please-action, https://github.com/gitleaks/gitleaks-action, https://github.com/pre-commit/action. Checked 2026-10-16.
- [S68] GitHub docs, service containers (PostgreSQL and Redis tutorials): https://github.com/github/docs/blob/main/content/actions/tutorials/use-containerized-services/create-postgresql-service-containers.md; rendered at https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers. Checked 2026-10-16.
- [S69] GitHub docs, hosted runner specs: https://github.com/github/docs/blob/main/data/reusables/actions/supported-github-runners.md; rendered at https://docs.github.com/en/actions/reference/runners/github-hosted-runners. Checked 2026-10-16.
- [S70] GitHub docs, push protection and security features: https://github.com/github/docs/blob/main/content/code-security/concepts/secret-security/push-protection.md and https://github.com/github/docs/blob/main/content/code-security/getting-started/github-security-features.md. Checked 2026-10-16.
- [S71] GitHub docs, Dependabot options reference: https://github.com/github/docs/blob/main/content/code-security/reference/supply-chain-security/dependabot-options-reference.md; rendered at https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference. Checked 2026-10-16.
- [S72] GitHub docs, CodeQL default setup and languages: https://github.com/github/docs/blob/main/content/code-security/how-tos/find-and-fix-code-vulnerabilities/configure-code-scanning/configure-code-scanning.md and https://github.com/github/docs/blob/main/data/reusables/code-scanning/codeql-languages-bullets.md. Checked 2026-10-16.
- [S73] Conventional Commits 1.0.0: https://www.conventionalcommits.org/en/v1.0.0/ (source https://github.com/conventional-commits/conventionalcommits.org). Checked 2026-10-16.
- [S74] release-please: https://www.npmjs.com/package/release-please (17.11.2), https://github.com/googleapis/release-please/blob/main/docs/customizing.md, https://github.com/googleapis/release-please-action/blob/v5.0.0/README.md. Checked 2026-10-16.
- [S75] Docker docs, Compose version and name; services healthcheck and mem_limit: https://github.com/docker/docs/blob/main/content/reference/compose-file/version-and-name.md and .../content/reference/compose-file/services.md (commit c12753f, 2026-10-15); rendered at https://docs.docker.com/reference/compose-file/version-and-name/ and https://docs.docker.com/reference/compose-file/services/. Checked 2026-10-16.
- [S76] Docker Compose tags and go.mod: https://github.com/docker/compose/tags and https://github.com/docker/compose/blob/v5.6.0/go.mod. Checked 2026-10-16.
- [S77] Docker Desktop settings (memory limit default): https://github.com/docker/docs/blob/main/content/manuals/desktop/settings-and-maintenance/settings.md; rendered at https://docs.docker.com/desktop/settings-and-maintenance/settings/. Checked 2026-10-16.
- [S78] pre-commit hook definitions: https://github.com/astral-sh/ruff-pre-commit/blob/v0.17.1/.pre-commit-hooks.yaml, https://github.com/astral-sh/uv-pre-commit (tag 0.13.1), https://github.com/gitleaks/gitleaks/blob/v8.30.1/.pre-commit-hooks.yaml. Checked 2026-10-16.
- [S79] GitHub docs, Actions billing (free for public repos on standard runners): https://github.com/github/docs/blob/main/content/billing/concepts/product-billing/github-actions.md. Checked 2026-10-16.
