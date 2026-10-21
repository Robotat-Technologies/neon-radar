# NeonRadar phase 3: Cypher and GDS for detection

Research date: 18 October 2026. Facts were checked against primary sources at fixed commits, cloned shallow and read on this machine (Cypher 5 and Cypher 25 manual sources, the Operations Manual 5.26 source, the GDS 2.13.14 manual and source, APOC Core 5.26.32 and APOC Extended 5.26 sources, the Neo4j 5.26.32 source, Python driver 6.4.1, testcontainers-python 4.15.0, docker-neo4j), plus PyPI, the Docker Hub API and neo4j.com pages. Every query in this note was linted with the project linter and with a stricter registry check (section 2.19). There was no Neo4j server or Docker daemon, so no query was executed: anything only a running server can confirm is marked UNVERIFIED.

## 0. Answers for the spec writer

1. **Cypher 5 in 5.26.** Use quantified relationships and quantified path patterns (QPP) with literal bounds, one rendered query per bound. Inside a QPP each iteration gets fresh variables: a predicate sees its own iteration and variables bound in an earlier `MATCH`, never the previous iteration [C1]. So strictly increasing `PAID.ts` cannot prune the expansion in Cypher 5. The recommended form: seek the first hop through `paid_ts`, then put `t.ts > t0.ts AND t.ts <= t0.ts + duration(...)` inside the QPP (applied per iteration), and finish with the post-filter `all(i IN range(0, size(t) - 2) WHERE t[i].ts < t[i + 1].ts)` [C2][N3]. The pruning form `allReduce()` is Cypher 25 only (2025.08) [C12]. 5.26 has only the default match mode and no path modes [C13]. `SHORTEST k`, `ALL SHORTEST`, `SHORTEST k GROUPS`, `ANY k` exist (5.21); prefer `ALL SHORTEST` for deterministic evidence [C1]. `COUNT {}`, `COLLECT {}`, `EXISTS {}`, `CALL (x) {}` (5.23) and `OPTIONAL CALL` (5.24) are available [C3]. Pass times as ISO strings into `datetime($p)`; durations never compare [C7]. Detectors need no APOC; APOC Extended functions are not in the image [A1][A2]. Section 1.10 lists the Cypher 25 features to avoid.

2. **Query design.** Each detector runs one to four bounded Cypher queries that retrieve candidates, then does the typology logic in Python. The queries are anchored on the `paid_ts` range seek or on a small label or id set, pruned inline, ordered by C2 ids and limited, with JSON-safe parameters. Python owns sliding windows, gaps, dwell times, sums per currency, partial ISO dates, peer statistics, effective shares, the OFAC-style fixpoint, deduplication and scoring (2.17). Section 2 gives lint-clean queries for all 14 typologies: 43 files, 78 rendered statements, 0 problems in both linters [L1]. Main pitfalls (2.18): id lookups must name `:Entity`; naive datetimes and `null` lists silently drop rows; undirected patterns count twice; sub-chains and joint holders duplicate alerts; hubs explode expansions. The Phase 1 circular-flow query shape is unanchored and should be replaced by the anchored form in 2.6 (same results).

3. **Performance.** The `paid_ts` index serves only a relationship the plan seeks directly (`DirectedRelationshipIndexSeekByRange`); an expansion from a node reads all of that node's `PAID` relationships [C9][C10]. The planner runs a QPP as `Repeat(Trail)` with per-iteration predicates inside (or as `VarLengthExpand` when a one-relationship QPP's node group variables are not used later); it also pushes outer `all(x IN group WHERE ...)` predicates inside, but not cross-iteration checks [N3]. Keep heap 2G and page cache 2G (standard profile) and add `db.memory.transaction.max` of about 1G [O1]. Run detector queries as `session.run(neo4j.Query(text, timeout=s))`: lazy, server-terminated on timeout, and never retried by the driver. Managed transactions retry `TransientError`, and the memory-limit error is one [D1][N9]. Latency figures are estimates: sub-second window scans, seconds to tens of seconds for anchored traversals (UNVERIFIED). Measure them with a benchmark command (3.6).

4. **GDS 2.13.** Community Edition has every algorithm. A concurrency above 4 fails with an error, and the model catalog holds 3 models [G1][G14]. Use the native `CALL gds.graph.project(name, nodes, rels, config)` or the Cypher projection aggregation `gds.graph.project(name, source, target, dataConfig, config)`; `gds.graph.project.cypher` is deprecated [G3][G4][G5]. Use `stream` (or `mutate`) and never `write`, which would add non-C2 properties. Determinism: the WCC partition is stable, but its ids are not [G6]. Louvain can vary at concurrency above 1 (parallel colouring, atomic sums), so use concurrency 1 [G15]. KNN needs `randomSeed` with concurrency 1 [G10]. Call GDS through the driver; skip `graphdatascience` 2.2: it is Apache-2.0 but caps `pyarrow` below 26, which conflicts with the Phase 2 pin [D3][K2]. GDS is GPLv3 in Neo4j's repository [G16]. Calling it over Bolt in a container NeonRadar does not ship is not conveying under GPLv3 (analysis, not legal advice) [G16]. For the mule ring, use WCC on a Cypher projection of the window's payments into fan-in candidates. Test it with sorted member sets and a Python union-find oracle (4.9).

5. **Testing.** Use `Neo4jContainer("neo4j:5.26.32-community")` (pin the digest) with `.with_env("NEO4J_PLUGINS", '["apoc", "graph-data-science"]')` and heap and page cache variables. The entrypoint adds `dbms.security.procedures.unrestricted=apoc.*,gds.*` itself. Setting that variable replaces the line, so list both [T2]. An allowlist restricts plugins only, and `gds.*` alone proves detectors are APOC-free [O3]. The default wait limit is 120 s [T1]. The image is about 352 MB compressed [T3]. Public runners have 4 CPUs and 16 GB; private ones have 2 CPUs and 8 GB [T4]. Assert sets of sorted edge-id tuples, the same alert ids across two runs, and `Decimal` money. In CI, run `EXPLAIN` on every query and fail on deprecation, cartesian-product or hint warnings and on any non-read query type [N10][D1].

6. **Community limits.** These do not block the design but shape it [O5]. No pipelined or parallel runtime: each query runs single-threaded, so run detectors in parallel sessions. No existence, type or key constraints: use `coalesce` and keep the invariant tests. One user database: use separate test containers and `run_id` tags. No `query.log`: time queries from Python [O4]. No page-cache warm-up: the first run is cold [O1]. No RBAC: use read access mode plus an `EXPLAIN` query-type check. GDS Community limits: drop graphs, no Arrow. `db.transaction.timeout` is labelled Enterprise in the manual but is in the Community code; the driver timeout works regardless [O1][N7][N8].

## 1. Cypher 5 in Neo4j 5.26 for detection

### 1.1 Which Cypher 5

- Neo4j 5.26 runs Cypher 5 only. Cypher 25 starts with Neo4j 2025.06, and from then "no new features will be added to Cypher 5" [C3].
- The Cypher 5 manual on its `cypher-5` branch documents Cypher 5 as it runs on 2026.x servers (`neo4j-version: '2026.09'` in its antora.yml). A few Cypher 5 items arrived after 5.26: `ON ERROR RETRY` for `CALL { } IN TRANSACTIONS` (2025.03), the planner's use of token indexes for dynamic labels (2025.08), the `MergeInto` operator (2025.11), and the `VECTOR` and `UUID` types (2025.10 and 2026.08, type only) [C3]. Check the version label of anything copied from the manual.
- The linter (`@neo4j-cypher/language-support` 2.0.0-next.39) follows this newer Cypher 5. It accepts `... IN TRANSACTIONS ... ON ERROR RETRY` under `CYPHER 5`, which 5.26 rejects [L1][K2].

### 1.2 Quantified path patterns and quantified relationships

- Introduced in 5.9 [C3]. Syntax: `((x)-[r:PAID]->(y) WHERE <predicate>){m,n}` (QPP) or `(a)-[r:PAID]->{m,n}(b)` (quantified relationship, a shorthand with only one relationship pattern) [C1].
- Quantifiers: `{m,n}`, `{n}`, `{m,}`, `{,n}`, `+`, `*`. Bounds are unsigned integer literals, never parameters [C1]. A quantified pattern must contain at least one relationship, QPPs cannot be nested, and a path pattern must have at least one element. The linter also rejects an upper bound of 0 ("A quantifier for a path pattern must not be limited by 0") [C1][L1].
- Group variables: a variable declared inside a QPP is a singleton inside it and a list outside it. For example, `t` is a relationship in the inner `WHERE` and a `LIST<RELATIONSHIP>` after the pattern [C1]. Using it as a singleton outside is an error. The linter catches it: `t.ts` on a group variable gives "Type mismatch ... but was List<Relationship>" [L1].
- Each iteration is matched with "a set of fresh variables", and adjacent iterations share only the juxtaposed node [C1].
- References: "Variables declared in a previous MATCH can be referenced inside of a quantified path pattern" [C1]. The 5.26.32 semantic check refuses a reference to a path variable of the same `MATCH`. It does not refuse a node or relationship variable of the same `MATCH` [N1][N2], but the manual only documents the previous-`MATCH` form. Always bind the anchor in a separate earlier `MATCH`.
- Uniqueness: "nodes can be revisited but relationships cannot" within one match of a graph pattern; across separate `MATCH` clauses relationships may repeat [C1]. The anchored queries in section 2 stay correct because the inline `t.ts > t0.ts` excludes the anchor relationship itself.
- Variable-length relationships `[*1..6]` are still legal Cypher 5 and are not flagged by the linter [L1]. The project rule bans them (PHASE-1.md 5.2) [K1], so add a regex check.

### 1.3 Comparing consecutive hops; strictly increasing PAID.ts

- A predicate inside a QPP cannot compare consecutive iterations. Fresh variables per iteration mean iteration i+1 cannot see iteration i's relationship [C1].
- A known workaround models transactions as nodes, so two consecutive transactions meet inside one iteration (`(tx_i)-[:TO]->(a_i)<-[:FROM]-(tx_j) WHERE tx_i.date < tx_j.date`) [P1][P2]. C2 is frozen with `PAID` as a relationship, so this is not available to NeonRadar [K1].
- What the 5.26.32 planner does: it lifts QPP predicates into a `ForAllRepetitions` form and moves them back into the inner plan, because that "can potentially short-circuit the expansion of the QPP". From the outer `WHERE` it moves only predicates of the form `all(x IN group WHERE p(x))` whose `p` does not use another group variable [N3]. `all(i IN range(0, size(t) - 2) WHERE t[i].ts < t[i + 1].ts)` does not have that form, so it runs as a post-filter after each full path is built.
- Recommended Cypher 5 form (from 2.5 and 2.6): the first hop is seeked through the index, and the window relative to it prunes every later hop:

```cypher
// Pattern: anchored, time-windowed, strictly time-ordered chain (rendered per qpp_max).
// lint-values: qpp_max=2,3
MATCH (a0:Account)-[t0:PAID]->(a1:Account)
WHERE t0.ts >= datetime($window_start) AND t0.ts < datetime($window_end)
MATCH (a1) ((x:Account)-[t:PAID]->(y:Account)
             WHERE t.ts > t0.ts AND t.ts <= t0.ts + duration({hours: $max_chain_hours})){1,{{qpp_max}}} (z:Account)
WHERE all(i IN range(0, size(t) - 2) WHERE t[i].ts < t[i + 1].ts)
RETURN [t0.id] + [r IN t | r.id] AS edge_ids
ORDER BY edge_ids
LIMIT $limit;
```

- Cypher 25 adds `allReduce(acc = init, x IN list | step, predicate)`. Its predicate "is inlined where applicable", which "allows for early pruning", and the manual's example checks that "each relationship's `since` value is greater than the previous one" [C12]. It is labelled "new 2025.08, Cypher 25 only". In Cypher 5 it fails to parse [L1].

### 1.4 Match modes, path modes and simple paths

- 5.26 has one match mode: the default, under which a relationship occurs at most once per `MATCH` result. The keyword `DIFFERENT RELATIONSHIPS` that names it and the mode `REPEATABLE ELEMENTS` are Cypher 25 only (2025.06). The path modes `WALK`, `TRAIL` and `ACYCLIC` are Cypher 25 only (2026.03), and `ACYCLIC` works with `SHORTEST` only from 2026.05 [C13][C14].
- The linter reports "Match modes such as `REPEATABLE ELEMENTS` are not supported in Cypher 5" and fails to parse `ACYCLIC` [L1].
- Simple paths in 5.26: write a list predicate over the path nodes, for example `all(i IN range(1, size(ns) - 1) WHERE NOT ns[i] IN ns[0..i])` (section 2), or `single(m IN nodes(p) WHERE m = n)` as in Phase 2 milestone 2.12 [K2]. A third idiom compares the size of `COUNT { UNWIND ... RETURN DISTINCT ... }` with the list size [P2].

### 1.5 Shortest path selectors

- `SHORTEST k`, `ALL SHORTEST` (equal to `SHORTEST 1 GROUP`), `SHORTEST k GROUPS`, `ANY k` and `ALL` arrived in 5.21 [C3][C1].
- Rules [C1]:
  - Paths are partitioned by distinct start and end node pairs.
  - Predicates inside the path pattern (node and relationship predicates, QPP predicates, parenthesized `WHERE`) are pre-filters; the graph pattern's `WHERE` is a post-filter.
  - A selective selector "must be the only path pattern in the graph pattern", so bind the start node in an earlier `MATCH`.
- Non-determinism: for `SHORTEST k`, "Where more than one path could be picked for a given length, there is no particular order in which that selection is done" [C1]. Use `ALL SHORTEST` and pick the smallest edge-id list in Python when evidence must be stable (2.15).
- Operators: `StatefulShortestPath(Into)` runs a bidirectional BFS between two bound nodes; `StatefulShortestPath(All)` runs a BFS from one node to many targets [C9]. So `ANY SHORTEST` from a bound node gives reachability without enumerating all paths (2.12).
- The legacy `shortestPath()` and `allShortestPaths()` take only a single variable-length relationship [C1]. The server warns when they are used with a fixed-length relationship [N10]. Do not use them.

### 1.6 COUNT, COLLECT and EXISTS subqueries

- `COUNT {}` and `EXISTS {}` (full forms since 5.3) and `COLLECT {}` (since 5.6) accept "any non-writing query" and can reference outer variables [C3][C4].
- `COLLECT` must end in a `RETURN` with exactly one column (the linter enforces it), keeps `null` values, and keeps the order of an `ORDER BY` in the subquery [C4][L1].
- The planner answers `COUNT { (n)-[:T]->() }` and `EXISTS { (n)-[:T]->() }` from the node's degree. This works only when the pattern has a type and direction but no label on the far node and no property predicate (`getDegreeRewriter`, which needs empty selections) [N4]. So `COUNT { (d)-[:DIRECTOR_OF]->() }` is cheap, and `COUNT { (d)-[:DIRECTOR_OF]->(:Organization) }` expands.

### 1.7 CALL (x) { } scoping

- The variable scope clause `CALL (a, b) { ... }`, `CALL (*) { ... }` and `CALL () { ... }` arrived in 5.23. The importing `WITH` and the naked `CALL { }` are deprecated, and the linter warns about them [C3][C5][L1].
- Rules [C5]:
  - Imported variables can be used anywhere in the subquery and cannot be aliased or redeclared there.
  - The subquery runs once per incoming row and cannot return a name that exists outside.
  - "If the subquery does not return any rows, there will be no rows available after the subquery" [C5]. An aggregation without grouping keys normally returns one row even on zero input (`count` gives 0, `collect` gives `[]`). The manual points to a knowledge-base article on this that could not be fetched here, so it is UNVERIFIED. The queries in section 2 work either way: they use `OPTIONAL MATCH` before counting (query 03) or drop empty results with `size(...) >= 1` (2.4).
- `OPTIONAL CALL` (5.24) keeps the outer row with `null` results [C3].
- `CALL { } IN TRANSACTIONS` is not needed by read-only detectors. It runs only in auto-commit transactions (PHASE-1.md 3.2) [K1].

### 1.8 Temporal values and parameters

- `PAID.ts` is a zoned `DATETIME` in UTC [K1]. Instants compare only with the same type [C7].
- Driver 6.4.1 sends a naive Python `datetime` as a `LOCAL DATETIME` (structure `d`) [D1]. Comparing it with `PAID.ts` gives `null`, so the row silently disappears [C7].
- Pass window bounds as ISO strings with `Z` and convert in Cypher: `r.ts >= datetime($window_start)`. Pass lengths as integers: `duration({days: $max_window_days})`. This also keeps `evidence.query.parameters` in the C4 alert valid JSON [K1].
- Elapsed time: `duration.inSeconds(a, b).seconds` (the manual: "Get the total seconds ... by returning the seconds component") or `b.epochMillis - a.epochMillis` [C6].
- Durations "cannot be directly compared": `duration1 < duration2` "will always return null" [C7].
- Duration components are truncated within their group (months, days, seconds). So `duration.between(a, b).days` ignores whole months, and `.seconds` ignores whole days. Use `duration.inDays(a, b).days` or `duration.inSeconds(a, b).seconds` [C6].
- `datetime.truncate('day', r.ts)` returns the zoned start of the day. `date(r.ts)` gives the UTC calendar date of a UTC `DATETIME`. `DATETIME + DURATION` and `DATETIME - DURATION` work [C6].
- Never call `datetime()` with no argument in a detector: it reads the clock, so a re-run would not reproduce. Pass the run's window instead.

### 1.9 Lists, reduce and ordered collect

- Available in 5.26: list comprehension, pattern comprehension, `reduce`, `range`, `size`, `head`, `last`, `tail`, `reverse`, slicing (`list[0..-1]`), `IN`, `+` and `||` concatenation (5.19), and `all`, `any`, `none` and `single` [C3][N6].
- `x IN $list` with a parameter list is evaluated with a cached hash lookup (`CachedIn`, "making the common <exp> IN <constant-expression> fast") [N5]. In Community, the slotted runtime interprets expressions; only Enterprise generates code for them [C11].
- Order of `collect()`: "When ORDER BY is present on a WITH clause, the immediately following clause will receive records in the specified order", which the manual uses to order `collect()` [C8]. Inside `COLLECT {}`, put `ORDER BY` before the `RETURN`. `collect(DISTINCT x)` order is not documented, so sort it in Python.
- `null` sorts last in ascending and first in descending order [C8]. Use `ORDER BY x IS NULL, x DESC` (Phase 2 3.2) [K2].

### 1.10 Cypher 25 only: never in a NeonRadar query

| Feature | Since | Source |
|---|---|---|
| `allReduce()` | 2025.08 | [C12] |
| `LET`, `FILTER`, `NEXT`, `WHEN ... ELSE`, `CYPHER 25` | 2025.06 | [C14] |
| `REPEATABLE ELEMENTS`, the `DIFFERENT RELATIONSHIPS` keyword | 2025.06 | [C13] |
| `vector()` and the vector functions | 2025.10 | [C14] |
| `coll.sort`, `coll.distinct`, `coll.flatten`, `coll.indexOf`, `coll.insert`, `coll.max`, `coll.min`, `coll.remove` | 2025.11 | [C14] |
| `SEARCH` (vector 2026.01, full-text 2026.09) | 2026.01 | [C14] |
| `ACYCLIC`, `TRAIL`, `WALK`, `PROPERTY_EXISTS()` | 2026.03 | [C13][C14] |
| `FOR` clause | 2026.04 | [C14] |
| `string.indexOf()` and the other new string functions | 2026.05 | [C14] |
| `cardinality()` | 2026.07 | [C14] |
| string interpolation `s"..."`, `uuid()` | 2026.08 | [C14] |
| map comprehension | 2026.09 | [C14] |
| `ON ERROR RETRY` (Cypher 5 on 2025.03+, not on 5.26) | 2025.03 | [C3] |

The plain linter does not catch `coll.sort` or `PROPERTY_EXISTS`. The strict registry check does (section 2.19) [L1].

### 1.11 APOC Core 5.26.32 and APOC Extended

- APOC Core 5.26.32 has 235 functions, 11 aggregation functions and 192 procedures (annotations in `core/src/main/java`) [A1]. The `apoc.agg` family is `first`, `last`, `nth`, `slice`, `median`, `percentiles`, `statistics`, `maxItems`, `minItems`, `product` and `graph`. `apoc.coll` includes `sortMaps`, `pairsMin`, `runningTotal`, `frequencies`, `toSet`, `zip` and `sum` [A1].
- In APOC 2025.07 and 2025.11, Neo4j deprecated most `apoc.coll.*` functions and `apoc.agg.graph` and `apoc.agg.product` under Cypher 25. The replacements are mostly Cypher 5 built-ins: `reduce()`, list comprehension, `value IN coll`, `COLLECT {}` with `ORDER BY`, and `stDev()` [A3]. Writing those built-ins now keeps detectors valid after a move to Cypher 25.
- Recommendation: no APOC in detector queries. Percentiles, medians and statistics belong in Python. `percentileCont` and `percentileDisc` exist as built-ins if needed [N6].
- APOC Extended (`neo4j-contrib/neo4j-apoc-procedures`, branch 5.26) is not in the image (PHASE-1.md 3.1) [K1]. In this domain it holds `apoc.agg.multiStats`, `apoc.agg.rollup`, `apoc.agg.row`, `apoc.agg.position`, `apoc.coll.avgDuration`, `apoc.coll.fillObject`, `apoc.temporal.overlap` and `apoc.algo.aStarWithPoint` [A2]. The strict check reports each as "not present in the database" [L1].

### 1.12 What the linters catch

| Check | `cypherlint/lint.mjs` (empty schema) | strict registry check |
|---|---|---|
| Syntax, Cypher 25 clauses (`LET`, `FILTER`), `allReduce`, match modes, `ACYCLIC` | yes | yes |
| Group variable misuse, path variable referenced inside its own QPP | yes | yes |
| Deprecations (`id()`, `CALL { WITH ... }`) | yes | yes |
| Unknown functions (`coll.sort`, `PROPERTY_EXISTS`, APOC Extended) | no | yes |
| Unknown procedures, wrong `YIELD` columns, deprecated `gds.graph.project.cypher` | no | yes |
| `[*1..3]`, `ON ERROR RETRY`, `datetime()` without argument | no | no (add regex rules) |

Recommendation for the spec: extend `make cypher-lint` with a function and procedure registry exported once from a running 5.26.32 container (`SHOW FUNCTIONS YIELD *` and `SHOW PROCEDURES YIELD *`) and committed. Add regex rules for `[*`, `id(`, `ON ERROR RETRY`, `datetime()`, `shortestPath(` and `apoc.periodic.iterate`.

## 2. Query design per typology

### 2.1 Conventions for every detector query

- Two stages. Cypher retrieves bounded candidates with evidence ids. Python applies windows, gaps, dwell times and sums, then scores and builds C4 alerts. Python never builds Cypher from data. Quantifier bounds come from one rendered template per allowed value, with a `// lint-values:` header as in PHASE-2.md [K1][K2].
- Parameters: `$window_start` and `$window_end` as UTC ISO strings (`[start, end)`), durations as integers (`$max_dwell_hours`, `$max_window_days`), id lists as lists and never `null`, and `$limit` always.
- Lookups by id name the `:Entity` label: `MATCH (a:Entity:Account {id: $id})`. The uniqueness constraint is on `:Entity(id)`, so `(a:Account {id: $id})` cannot use it [K1].
- Return C2 `id` values, never `elementId()` or GDS node ids. Order every result by C2 ids, and order every list before collecting it. Return `ts.epochMillis` so Python does integer arithmetic.
- Treat a run that hits `$limit` as truncated: warn, and narrow the window or raise the limit. Never silently score a cut list.
- Hubs: accounts with many outbound payments in the window (query 01) are passed as `$hub_account_ids` and excluded from chain and cycle expansion. Python reports them as payment-service or payroll look-alikes.
- Directions (C2): `PAID` payer account to beneficiary account; `HOLDS_ACCOUNT` holder to account; `OWNS` owner to owned; `CONTROLS` controller to controlled; `DIRECTOR_OF` director to organisation; `HAS_ADDRESS` entity to address; `REPRESENTS` agent to client; `SUBJECT_OF` entity to sanction [K1]. `FAMILY_OF` and `ASSOCIATE_OF` are stored one way but are symmetric, so always query them undirected. `CONSOLIDATES` is accounting consolidation, never ownership [K2]. `POSSIBLY_SAME_AS` is never traversed [K2]. `LINKED_TO` is not used.

### 2.2 Shared queries

Each block below is labelled with its file name, and the text refers to a query by its two-digit prefix (query 03 is `03_common_account_activity.cypher`).

Query `00_common_holders.cypher`:

```cypher
// common: holders and flags for a batch of evidence accounts (C4 subjects, wording_class, data_flags).
// The uniqueness constraint is on :Entity(id), so every lookup by id names the :Entity label.
UNWIND $account_ids AS account_id
MATCH (a:Entity:Account {id: account_id})
OPTIONAL MATCH (h:LegalEntity)-[ha:HOLDS_ACCOUNT]->(a)
WITH a, h, ha
ORDER BY a.id, h.id
RETURN a.id AS account_id, a.synthetic AS account_synthetic, a.account_kind AS account_kind,
       a.opening_date AS opening_date,
       collect(CASE WHEN h IS NULL THEN null ELSE {holder_id: h.id, caption: h.caption,
               synthetic: h.synthetic, is_person: h:Person, is_company: h:Company,
               sanctioned: h:Sanctioned, pep: h:PEP, rca: h:RCA, role: ha.role} END) AS holders
ORDER BY account_id;
```

Query `01_common_hub_accounts.cypher`:

```cypher
// common: accounts whose outbound payment count in the window reaches the cap. Python passes the result
// as $hub_account_ids to the chain and cycle queries, which never expand through these accounts.
MATCH (a:Account)-[r:PAID]->(:Account)
WHERE r.ts >= datetime($window_start) AND r.ts < datetime($window_end)
WITH a, count(r) AS out_payments
WHERE out_payments >= $hub_min_out_payments
RETURN a.id AS account_id, a.account_kind AS account_kind, out_payments
ORDER BY out_payments DESC, account_id
LIMIT $limit;
```

Query `02_common_payments_among_companies.cypher`:

```cypher
// common: payments in the window between accounts held by companies of one cluster
// (same registered address, same formation agent or same director).
UNWIND $company_ids AS company_id
MATCH (c1:Entity:Company {id: company_id})-[:HOLDS_ACCOUNT]->(x:Account)-[r:PAID]->(y:Account)<-[:HOLDS_ACCOUNT]-(c2:Company)
WHERE c2.id IN $company_ids AND c2 <> c1
  AND r.ts >= datetime($window_start) AND r.ts < datetime($window_end)
RETURN c1.id AS payer_company_id, c2.id AS payee_company_id, x.id AS payer_account_id,
       y.id AS payee_account_id, r.id AS edge_id, r.ts.epochMillis AS ts_ms, r.amount AS amount,
       r.currency AS currency
ORDER BY ts_ms, edge_id
LIMIT $limit;
```

Query `03_common_account_activity.cypher`:

```cypher
// common: activity profile of a batch of accounts in the window (counts only; amounts are summed per
// currency in Python). Used for "little other activity" and payroll or supplier look-alike checks.
UNWIND $account_ids AS account_id
MATCH (a:Entity:Account {id: account_id})
CALL (a) {
  OPTIONAL MATCH (a)-[r:PAID]->(dst:Account)
  WHERE r.ts >= datetime($window_start) AND r.ts < datetime($window_end)
  RETURN count(r) AS out_payments, count(DISTINCT dst) AS out_counterparties
}
CALL (a) {
  OPTIONAL MATCH (src:Account)-[r:PAID]->(a)
  WHERE r.ts >= datetime($window_start) AND r.ts < datetime($window_end)
  RETURN count(r) AS in_payments, count(DISTINCT src) AS in_counterparties
}
RETURN a.id AS account_id, out_payments, out_counterparties, in_payments, in_counterparties
ORDER BY account_id;
```

### 2.3 structuring

Pattern (7.2 item 1): many `cash_deposit` payments from `cash_ledger` accounts into one account, or into several accounts of one holder, just below a threshold, within a short window, often across branches, with a daily total above the threshold [K1]. Cypher seeks the window and filters the band. Python computes `band_low = threshold x (1 - band)` and passes it. Python also handles the UTC day buckets (`ts_ms // 86400000`), the sliding window, the branch count, the daily total rule, and look-alikes such as regular takings.

Query `10_structuring_account.cypher`:

```cypher
// structuring (account form): near-threshold cash deposits from branch cash ledgers in the window,
// grouped per receiving account and currency, in time order. Entry point: paid_ts range seek.
// Python applies the UTC day buckets, the sliding window, the branch count and the daily total rule.
MATCH (branch:Account)-[r:PAID]->(acct:Account)
WHERE r.ts >= datetime($window_start) AND r.ts < datetime($window_end)
  AND r.channel = 'cash_deposit'
  AND branch.account_kind = 'cash_ledger'
  AND r.amount >= $band_low AND r.amount < $threshold
WITH acct, branch, r
ORDER BY r.ts, r.id
WITH acct, r.currency AS currency,
     collect({edge_id: r.id, ts_ms: r.ts.epochMillis, amount: r.amount, branch_id: branch.id}) AS deposits
WHERE size(deposits) >= $min_deposits
RETURN acct.id AS account_id, currency, size(deposits) AS deposit_count, deposits
ORDER BY account_id, currency
LIMIT $limit;
```

Query `11_structuring_holder.cypher`:

```cypher
// structuring (holder form): near-threshold cash deposits into two or more accounts of one holder.
// A joint account appears under each of its holders; Python removes duplicate alerts by edge ids.
MATCH (branch:Account)-[r:PAID]->(acct:Account)<-[:HOLDS_ACCOUNT]-(holder:LegalEntity)
WHERE r.ts >= datetime($window_start) AND r.ts < datetime($window_end)
  AND r.channel = 'cash_deposit'
  AND branch.account_kind = 'cash_ledger'
  AND r.amount >= $band_low AND r.amount < $threshold
WITH holder, acct, branch, r
ORDER BY r.ts, r.id
WITH holder, r.currency AS currency, count(DISTINCT acct) AS accounts,
     collect({edge_id: r.id, ts_ms: r.ts.epochMillis, amount: r.amount, account_id: acct.id,
              branch_id: branch.id}) AS deposits
WHERE accounts >= 2 AND size(deposits) >= $min_deposits
RETURN holder.id AS holder_id, currency, accounts, deposits
ORDER BY holder_id, currency
LIMIT $limit;
```

### 2.4 rapid_pass_through

Pattern (7.2 item 2): inbound payments to an account in a window that leave again within hours or days, keeping a small residual. Inbound comes from several unrelated accounts, outbound goes to few beneficiaries [K1]. Python matches inflows to outflows first in, first out, per currency, and computes the dwell times, residual ratio and counterparty counts. A second call of query 03 or 18 gives the "unrelated senders" facts.

Query `12_rapid_pass_through.cypher`:

```cypher
// rapid_pass_through: customer accounts with inbound payments in the window, with their outbound payments
// up to the window end plus the longest dwell time. Python matches inflows to outflows (first in, first out)
// per currency and computes dwell times and the residual. Accounts above $max_inbound are skipped here and
// reported by Python as payment-service look-alikes.
MATCH (src:Account)-[r_in:PAID]->(acct:Account)
WHERE r_in.ts >= datetime($window_start) AND r_in.ts < datetime($window_end)
  AND acct.account_kind = 'customer'
WITH acct, src, r_in
ORDER BY r_in.ts, r_in.id
WITH acct, collect({edge_id: r_in.id, ts_ms: r_in.ts.epochMillis, amount: r_in.amount,
                    currency: r_in.currency, counterparty_id: src.id}) AS inbound
WHERE size(inbound) >= $min_inbound AND size(inbound) <= $max_inbound
CALL (acct) {
  MATCH (acct)-[r_out:PAID]->(dst:Account)
  WHERE r_out.ts >= datetime($window_start)
    AND r_out.ts < datetime($window_end) + duration({hours: $max_dwell_hours})
  WITH r_out, dst
  ORDER BY r_out.ts, r_out.id
  RETURN collect({edge_id: r_out.id, ts_ms: r_out.ts.epochMillis, amount: r_out.amount,
                  currency: r_out.currency, channel: r_out.channel, counterparty_id: dst.id}) AS outbound
}
WITH acct, inbound, outbound
WHERE size(outbound) >= 1
RETURN acct.id AS account_id, inbound, outbound
ORDER BY account_id
LIMIT $limit;
```

### 2.5 layering_chain

Pattern (7.2 item 3): a time-ordered path of three or more `PAID` hops through accounts of different holders, with short dwell, slightly shrinking amounts, and intermediates with little other activity [K1]. Cypher finds chains anchored at an indexed first hop, with every later hop inside the chain window, in the same currency and within an amount band of the first hop.

Python handles the rest:

- dwell per hop and the hop-to-hop shrink ratio;
- distinct holders (query 00), little other activity (query 03), and shared address, agent or director;
- keeping only maximal chains: a chain found from a later anchor is a suffix of one found from an earlier anchor, and is dropped.

Split-and-merge layering (fan-out then fan-in) is not a path; detect it from fan-out and fan-in candidates that share accounts.

Query `13_layering_chain.cypher`:

```cypher
// layering_chain: time-ordered chains of 3 to qpp_max + 1 PAID hops through customer accounts.
// One rendered query per qpp_max (quantifier bounds cannot be parameters). The first hop is seeked
// through the paid_ts index; every later hop must fall after it and inside the chain window (inline,
// so the expansion is pruned); strict ordering between consecutive hops is a post-filter.
// lint-values: qpp_max=2,3,4,5,6,7
MATCH (a0:Account)-[t0:PAID]->(a1:Account)
WHERE t0.ts >= datetime($window_start) AND t0.ts < datetime($window_end)
  AND t0.amount >= $min_amount
  AND a0.account_kind = 'customer' AND a1.account_kind = 'customer'
  AND NOT a1.id IN $hub_account_ids
MATCH (a1) ((x:Account)-[t:PAID]->(y:Account)
             WHERE t.ts > t0.ts AND t.ts <= t0.ts + duration({hours: $max_chain_hours})
               AND t.currency = t0.currency
               AND t.amount <= t0.amount * $max_amount_ratio
               AND t.amount >= t0.amount * $min_amount_ratio
               AND y.account_kind = 'customer'
               AND NOT y.id IN $hub_account_ids){2,{{qpp_max}}} (z:Account)
WHERE all(i IN range(0, size(t) - 2) WHERE t[i].ts < t[i + 1].ts)
WITH t0, t, [a0, a1] + y AS accounts
WHERE all(i IN range(1, size(accounts) - 1) WHERE NOT accounts[i] IN accounts[0..i])
RETURN [n IN accounts | n.id] AS account_ids,
       [t0.id] + [r IN t | r.id] AS edge_ids,
       [t0.ts.epochMillis] + [r IN t | r.ts.epochMillis] AS ts_ms,
       [t0.amount] + [r IN t | r.amount] AS amounts,
       t0.currency AS currency
ORDER BY edge_ids
LIMIT $limit;
```

### 2.6 circular_flow

The Phase 1 query starts from every `Account` with `(a:Account)-[t:PAID]->{2,6}(a)` and applies the time order as a post-filter (M1.9b) [K1]. On 2 million `PAID` relationships it expands every trail of up to 6 hops from every account and keeps those that close, before any time filter. The manual warns that, without bounds and inline predicates, "the execution time will increase exponentially" [C2].

The anchored form below returns the same cycles under the M1.9b rules:

- hops strictly time-ordered;
- intermediates distinct;
- `t[-1].ts - t[0].ts` within the window, because every later hop is at most `max_window_days` after the anchor;
- the return ratio checked;
- each cycle found once, from its earliest payment.

It adds the requirement that the first hop lies in the run window. Keep the Phase 1 fixture cases A to F as its regression test.

Cycle length is `1 + size(t)`. Python drops lengths below `min_hops`. The same-holder variant is the Phase 3 addition named in M1.9b.

Query `14_circular_flow_anchored.cypher`:

```cypher
// circular_flow (Phase 3 shape of the M1.9b query): cycles that return to the originating account,
// anchored at an indexed first hop. Because every later hop must be later than the anchor, each cycle
// is found exactly once, from its earliest payment. Cycle length = 1 + size(t), from 2 to qpp_max + 1.
// lint-values: qpp_max=1,2,3,4,5,6,7
MATCH (a:Account)-[t0:PAID]->(n1:Account)
WHERE t0.ts >= datetime($window_start) AND t0.ts < datetime($window_end)
  AND a.account_kind = 'customer' AND n1 <> a
  AND NOT n1.id IN $hub_account_ids
MATCH (n1) ((x:Account)-[t:PAID]->(y:Account)
             WHERE t.ts > t0.ts AND t.ts <= t0.ts + duration({days: $max_window_days})
               AND t.currency = t0.currency
               AND NOT y.id IN $hub_account_ids){1,{{qpp_max}}} (a)
WHERE all(i IN range(0, size(t) - 2) WHERE t[i].ts < t[i + 1].ts)
WITH a, t0, t, [a, n1] + y[0..-1] AS accounts
WHERE all(i IN range(1, size(accounts) - 1) WHERE NOT accounts[i] IN accounts[0..i])
  AND t[-1].amount >= t0.amount * $min_return_ratio
RETURN a.id AS origin_id, [n IN accounts | n.id] AS account_ids,
       [t0.id] + [r IN t | r.id] AS edge_ids,
       [t0.ts.epochMillis] + [r IN t | r.ts.epochMillis] AS ts_ms,
       [t0.amount] + [r IN t | r.amount] AS amounts,
       t0.currency AS currency
ORDER BY edge_ids
LIMIT $limit;
```

Query `15_circular_flow_same_holder.cypher`:

```cypher
// circular_flow (same-holder form): funds leave one account and return to a different account of the
// same holder. holder is bound before the quantified path pattern, so the final hop is an equijoin.
// lint-values: qpp_max=1,2,3,4,5,6,7
MATCH (holder:LegalEntity)-[:HOLDS_ACCOUNT]->(a:Account)-[t0:PAID]->(n1:Account)
WHERE t0.ts >= datetime($window_start) AND t0.ts < datetime($window_end)
  AND a.account_kind = 'customer' AND n1 <> a
  AND NOT n1.id IN $hub_account_ids
MATCH (n1) ((x:Account)-[t:PAID]->(y:Account)
             WHERE t.ts > t0.ts AND t.ts <= t0.ts + duration({days: $max_window_days})
               AND t.currency = t0.currency
               AND NOT y.id IN $hub_account_ids){1,{{qpp_max}}} (b:Account)<-[:HOLDS_ACCOUNT]-(holder)
WHERE b <> a
  AND all(i IN range(0, size(t) - 2) WHERE t[i].ts < t[i + 1].ts)
WITH holder, a, b, t0, t, [a, n1] + y AS accounts
WHERE all(i IN range(1, size(accounts) - 1) WHERE NOT accounts[i] IN accounts[0..i])
  AND t[-1].amount >= t0.amount * $min_return_ratio
RETURN holder.id AS holder_id, a.id AS origin_id, b.id AS return_account_id,
       [n IN accounts | n.id] AS account_ids,
       [t0.id] + [r IN t | r.id] AS edge_ids,
       [t0.ts.epochMillis] + [r IN t | r.ts.epochMillis] AS ts_ms,
       [t0.amount] + [r IN t | r.amount] AS amounts,
       t0.currency AS currency
ORDER BY edge_ids
LIMIT $limit;
```

Optional prefilter: a time-ordered cycle is also a cycle in the static graph, so GDS strongly connected components (`gds.scc`, production tier [G13]) over the window's `PAID` edges could narrow the anchors. This is only worth adding if measurements (3.6) show the anchored query is too slow.

### 2.7 fan_in_collection

Pattern (7.2 item 5): many person-held accounts, with no earlier relationship to the collector or to each other, pay one account in a short window. They are often recently opened, and onward transfers or cash withdrawals follow [K1].

Stage 1 finds collectors. Stage 2 lists their senders with earlier contact and holders. Stage 3 finds earlier links among senders. Stage 4 (query 19, shared with fan-out) returns the onward flows. Python parses the partial `opening_date`, scores, and applies the look-alikes (charities, crowdfunding, landlords). The ring variant is in 4.9.

Query `16_fan_in_collectors.cypher`:

```cypher
// fan_in_collection, stage 1: collector accounts paid by many distinct customer accounts in the window.
MATCH (src:Account)-[r:PAID]->(c:Account)
WHERE r.ts >= datetime($window_start) AND r.ts < datetime($window_end)
  AND src.account_kind = 'customer' AND c.account_kind = 'customer'
WITH c, r.currency AS currency, count(DISTINCT src) AS senders, count(r) AS payments
WHERE senders >= $min_senders
RETURN c.id AS collector_id, currency, senders, payments
ORDER BY senders DESC, collector_id, currency
LIMIT $limit;
```

Query `17_fan_in_senders.cypher`:

```cypher
// fan_in_collection, stage 2: the senders of each candidate collector, with earlier contact and holders.
// Python parses opening_date (it may be partial, for example "2026" or "2026-03").
UNWIND $collector_ids AS collector_id
MATCH (c:Entity:Account {id: collector_id})
MATCH (src:Account)-[r:PAID]->(c)
WHERE r.ts >= datetime($window_start) AND r.ts < datetime($window_end)
  AND src.account_kind = 'customer'
WITH c, src, r
ORDER BY r.ts, r.id
WITH c, src, collect({edge_id: r.id, ts_ms: r.ts.epochMillis, amount: r.amount, currency: r.currency}) AS payments
RETURN c.id AS collector_id, src.id AS sender_id, src.opening_date AS sender_opening_date,
       EXISTS { (src)-[e:PAID]-(c) WHERE e.ts < datetime($window_start) } AS prior_contact,
       COLLECT { MATCH (h:LegalEntity)-[:HOLDS_ACCOUNT]->(src) RETURN h.id ORDER BY h.id } AS holder_ids,
       COLLECT { MATCH (h:Person)-[:HOLDS_ACCOUNT]->(src) RETURN h.id ORDER BY h.id } AS person_holder_ids,
       payments
ORDER BY collector_id, sender_id
LIMIT $limit;
```

Query `18_fan_in_sender_links.cypher`:

```cypher
// fan_in_collection, stage 3: payments before the window between senders of one collector
// (senders that already knew each other weaken the pattern).
UNWIND $sender_ids AS sender_id
MATCH (s1:Entity:Account {id: sender_id})-[e:PAID]-(s2:Account)
WHERE s2.id IN $sender_ids AND s1.id < s2.id
  AND e.ts < datetime($window_start)
RETURN s1.id AS sender_a, s2.id AS sender_b, count(e) AS earlier_payments
ORDER BY sender_a, sender_b
LIMIT $limit;
```

Query `19_onward_flows.cypher`:

```cypher
// fan_in_collection stage 4 and fan_out_distribution stage 3: what a batch of accounts did next
// (onward transfers and cash withdrawals) up to the window end plus the dwell limit.
UNWIND $account_ids AS account_id
MATCH (a:Entity:Account {id: account_id})-[o:PAID]->(dst:Account)
WHERE o.ts >= datetime($window_start)
  AND o.ts < datetime($window_end) + duration({hours: $max_dwell_hours})
WITH a, o, dst
ORDER BY o.ts, o.id
RETURN a.id AS account_id,
       collect({edge_id: o.id, ts_ms: o.ts.epochMillis, amount: o.amount, currency: o.currency,
                channel: o.channel, counterparty_id: dst.id,
                to_cash: dst.account_kind = 'cash_ledger'}) AS outbound
ORDER BY account_id;
```

### 2.8 fan_out_distribution

Pattern (7.2 item 6): one account pays many accounts in a short window, with similar or round amounts, to recipients without earlier relationship. Cash withdrawals or a second layer of transfers follow [K1].

Python computes the amount dispersion and round amounts. Use integer cents, `round(amount * 100)`, never float modulo. It also checks the regular cadence of payroll and the other look-alikes (supplier batches, dividends, refunds).

Query `24_fan_out_distributors.cypher`:

```cypher
// fan_out_distribution, stage 1: accounts paying many distinct customer accounts in the window.
MATCH (d:Account)-[r:PAID]->(dst:Account)
WHERE r.ts >= datetime($window_start) AND r.ts < datetime($window_end)
  AND d.account_kind = 'customer' AND dst.account_kind = 'customer'
WITH d, r.currency AS currency, count(DISTINCT dst) AS recipients, count(r) AS payments
WHERE recipients >= $min_recipients
RETURN d.id AS distributor_id, currency, recipients, payments
ORDER BY recipients DESC, distributor_id, currency
LIMIT $limit;
```

Query `25_fan_out_recipients.cypher`:

```cypher
// fan_out_distribution, stage 2: recipients of each candidate, earlier contact, and what they did next.
UNWIND $distributor_ids AS distributor_id
MATCH (d:Entity:Account {id: distributor_id})-[r:PAID]->(dst:Account)
WHERE r.ts >= datetime($window_start) AND r.ts < datetime($window_end)
  AND dst.account_kind = 'customer'
WITH d, dst, r
ORDER BY r.ts, r.id
WITH d, dst, collect({edge_id: r.id, ts_ms: r.ts.epochMillis, amount: r.amount, currency: r.currency}) AS received
RETURN d.id AS distributor_id, dst.id AS recipient_id,
       EXISTS { (d)-[e:PAID]-(dst) WHERE e.ts < datetime($window_start) } AS prior_contact,
       received,
       COLLECT { MATCH (dst)-[o:PAID]->(n:Account)
                 WHERE o.ts >= datetime($window_start)
                   AND o.ts < datetime($window_end) + duration({hours: $max_dwell_hours})
                 WITH o, n
                 ORDER BY o.ts, o.id
                 RETURN {edge_id: o.id, ts_ms: o.ts.epochMillis, amount: o.amount, channel: o.channel,
                         counterparty_id: n.id, to_cash: n.account_kind = 'cash_ledger'} } AS onward
ORDER BY distributor_id, recipient_id
LIMIT $limit;
```

### 2.9 dormant_reactivation

Pattern (7.2 item 7): no `PAID` for a long gap (default 180 days), then a burst of inbound and outbound volume. This often follows soon after a new `DIRECTOR_OF` or `OWNS` on the holder. In the company variant, a new or long-dormant company suddenly moves large sums [K1].

Set `$lookback_days` above `$min_gap_days`. A `null` `last_before` means either no payment within the lookback or a new account. Python tells them apart with `opening_date` and compares the partial dates of stage 2 with the first burst payment.

Query `26_dormant_reactivation.cypher`:

```cypher
// dormant_reactivation: customer accounts with a burst of payments in the window whose previous payment
// lies at least $min_gap_days before the first burst payment, or that have none within the lookback.
// The undirected pattern sees each payment once from each end; the account_kind filter keeps the customer end.
MATCH (acct:Account)-[r:PAID]-(:Account)
WHERE r.ts >= datetime($window_start) AND r.ts < datetime($window_end)
  AND acct.account_kind = 'customer'
WITH acct, count(r) AS burst_payments, min(r.ts) AS first_burst_ts,
     sum(CASE WHEN startNode(r) = acct THEN 1 ELSE 0 END) AS outbound_payments
WHERE burst_payments >= $min_burst_payments
CALL (acct, first_burst_ts) {
  OPTIONAL MATCH (acct)-[p:PAID]-(:Account)
  WHERE p.ts < first_burst_ts AND p.ts >= first_burst_ts - duration({days: $lookback_days})
  RETURN max(p.ts) AS last_before
}
WITH acct, burst_payments, outbound_payments, first_burst_ts, last_before
WHERE last_before IS NULL OR last_before <= first_burst_ts - duration({days: $min_gap_days})
RETURN acct.id AS account_id, acct.opening_date AS opening_date,
       burst_payments, outbound_payments, burst_payments - outbound_payments AS inbound_payments,
       first_burst_ts.epochMillis AS first_burst_ms,
       CASE WHEN last_before IS NULL THEN null ELSE last_before.epochMillis END AS last_before_ms
ORDER BY account_id
LIMIT $limit;
```

Query `27_dormant_holder_changes.cypher`:

```cypher
// dormant_reactivation, stage 2: holder facts for the date checks done in Python (new director or owner,
// incorporation date). All dates here are ISO strings and may be partial.
UNWIND $account_ids AS account_id
MATCH (acct:Entity:Account {id: account_id})<-[:HOLDS_ACCOUNT]-(h:LegalEntity)
RETURN acct.id AS account_id, h.id AS holder_id, h.incorporation_date AS incorporation_date,
       COLLECT { MATCH (d:LegalEntity)-[dr:DIRECTOR_OF]->(h)
                 RETURN {director_id: d.id, start_date: dr.start_date, end_date: dr.end_date,
                         is_nominee: coalesce(dr.is_nominee, false)} AS item
                 ORDER BY item.director_id } AS directorships,
       COLLECT { MATCH (o:LegalEntity)-[ow:OWNS]->(h)
                 RETURN {owner_id: o.id, start_date: ow.start_date, end_date: ow.end_date} AS item
                 ORDER BY item.owner_id } AS ownerships
ORDER BY account_id, holder_id;
```

### 2.10 shell_chain

Pattern (7.2 item 8): an `OWNS` chain of two or more company layers, often across jurisdictions, ending at a person, at a company with no recorded owner, or looping back. Look for nominee directors or directors with many appointments, and companies that move money without a payroll or supplier pattern [K1].

The candidate stage avoids enumerating every chain in a register-sized graph. The upward chains are anchored at each candidate. Python keeps maximal chains, counts jurisdictions, and judges the money profile with query 03.

Query `30_shell_chain_candidates.cypher`:

```cypher
// shell_chain, stage 1: companies with a nominee director, a nominee shareholding, or a director who holds
// at least $min_appointments appointments. The inner COUNT has no label or property filter, so the planner
// answers it from the node's degree (getDegreeRewriter) instead of expanding.
MATCH (c:Company)
WHERE EXISTS { (:LegalEntity)-[d:DIRECTOR_OF]->(c) WHERE d.is_nominee = true }
   OR EXISTS { (:LegalEntity)-[o:OWNS]->(c) WHERE o.is_nominee = true }
   OR EXISTS { (dir:LegalEntity)-[:DIRECTOR_OF]->(c) WHERE COUNT { (dir)-[:DIRECTOR_OF]->() } >= $min_appointments }
RETURN c.id AS company_id
ORDER BY company_id
LIMIT $limit;
```

Query `31_shell_chain_up.cypher`:

```cypher
// shell_chain, stage 2: OWNS chains of two to max_hops layers that end at each candidate company,
// simple paths only. Python keeps the maximal chains and drops their sub-chains.
// lint-values: max_hops=2,3,4,5,6
UNWIND $company_ids AS company_id
MATCH (bottom:Entity:Company {id: company_id})
MATCH p = (top:LegalEntity)-[o:OWNS]->{2,{{max_hops}}}(bottom)
WHERE all(i IN range(1, size(nodes(p)) - 1) WHERE NOT nodes(p)[i] IN nodes(p)[0..i])
RETURN bottom.id AS subject_id,
       [n IN nodes(p) | n.id] AS node_ids,
       [r IN o | r.id] AS edge_ids,
       [n IN nodes(p) | n.jurisdiction] AS jurisdictions,
       [n IN nodes(p) | CASE WHEN n:Person THEN 'person' WHEN n:Company THEN 'company' ELSE 'other' END] AS kinds,
       [r IN o | coalesce(r.is_nominee, false)] AS nominee_holdings,
       NOT EXISTS { (:LegalEntity)-[:OWNS]->(top) } AS top_has_no_recorded_owner
ORDER BY subject_id, size(edge_ids) DESC, node_ids
LIMIT $limit;
```

Query `32_shell_chain_loops.cypher`:

```cypher
// shell_chain, stage 2b: ownership loops that pass through a candidate company.
// lint-values: max_hops=2,3,4,5,6
UNWIND $company_ids AS company_id
MATCH (c:Entity:Company {id: company_id})
MATCH p = (c)-[o:OWNS]->{2,{{max_hops}}}(c)
WHERE all(i IN range(1, size(nodes(p)) - 2) WHERE NOT nodes(p)[i] IN nodes(p)[0..i])
RETURN c.id AS company_id, [n IN nodes(p) | n.id] AS node_ids, [r IN o | r.id] AS edge_ids
ORDER BY company_id, node_ids
LIMIT $limit;
```

Query `33_shell_chain_company_facts.cypher`:

```cypher
// shell_chain, stage 3: directors (nominee flag, appointment count) and accounts of the chain companies.
UNWIND $company_ids AS company_id
MATCH (c:Entity:Company {id: company_id})
RETURN c.id AS company_id, c.jurisdiction AS jurisdiction, c.incorporation_date AS incorporation_date,
       COLLECT { MATCH (d:LegalEntity)-[dr:DIRECTOR_OF]->(c)
                 RETURN {director_id: d.id, is_nominee: coalesce(dr.is_nominee, false),
                         appointments: COUNT { (d)-[:DIRECTOR_OF]->() }} AS item
                 ORDER BY item.director_id } AS directors,
       COLLECT { MATCH (c)-[:HOLDS_ACCOUNT]->(a:Account) RETURN a.id ORDER BY a.id } AS account_ids
ORDER BY company_id;
```

### 2.11 mass_registration_address

Pattern (7.2 item 9): an `Address` with many incoming `HAS_ADDRESS {role: 'registered'}`. The pattern is stronger when companies at the address pay each other [K1]. Count by node and by `address_key`, which Phase 2 always sets, to see normalisation look-alikes [K2]. Python compares the two counts and applies the registered-agent look-alike.

Query `34_mass_registration_address.cypher`:

```cypher
// mass_registration_address, stage 1: addresses with many registered companies.
MATCH (addr:Address)
WITH addr, COUNT { (c:Company)-[h:HAS_ADDRESS]->(addr) WHERE h.role = 'registered' } AS companies
WHERE companies >= $min_companies
RETURN addr.id AS address_id, addr.address_key AS address_key, addr.country AS country, companies
ORDER BY companies DESC, address_id
LIMIT $limit;
```

Query `35_mass_registration_by_key.cypher`:

```cypher
// mass_registration_address, stage 1b: the same count by normalised address_key, which merges Address
// nodes that differ only in spelling. Python sorts address_ids (collect order is not defined here).
MATCH (c:Company)-[h:HAS_ADDRESS]->(addr:Address)
WHERE h.role = 'registered' AND addr.address_key IS NOT NULL
WITH addr.address_key AS address_key, count(DISTINCT c) AS companies, collect(DISTINCT addr.id) AS address_ids
WHERE companies >= $min_companies
RETURN address_key, companies, address_ids
ORDER BY companies DESC, address_key
LIMIT $limit;
```

Query `36_mass_registration_payments.cypher`:

```cypher
// mass_registration_address, stage 2: payments in the window between companies registered at one address.
UNWIND $address_ids AS address_id
MATCH (addr:Entity:Address {id: address_id})<-[h1:HAS_ADDRESS]-(c1:Company)-[:HOLDS_ACCOUNT]->(x:Account)
MATCH (x)-[r:PAID]->(y:Account)<-[:HOLDS_ACCOUNT]-(c2:Company)-[h2:HAS_ADDRESS]->(addr)
WHERE h1.role = 'registered' AND h2.role = 'registered' AND c1 <> c2
  AND r.ts >= datetime($window_start) AND r.ts < datetime($window_end)
RETURN addr.id AS address_id, c1.id AS payer_company_id, c2.id AS payee_company_id,
       r.id AS edge_id, r.ts.epochMillis AS ts_ms, r.amount AS amount, r.currency AS currency
ORDER BY address_id, ts_ms, edge_id
LIMIT $limit;
```

### 2.12 sanctions_exposure

Pattern (7.2 item 10): `OWNS` paths of at most 6 hops from `:Sanctioned` nodes. Each sanctioned owner's effective share is a range: the sum over its paths of the products of the band bounds. This is a teaching metric. An OFAC-style flag passes blocked status down the chain. `CONTROLS` and `DIRECTOR_OF` create exposure without ownership [K1].

Returning every path from Cypher repeats shared edges in every row and can grow exponentially in a dense ownership graph. So Cypher returns the reachable edge set once (one breadth-first shortest path per reached node, `StatefulShortestPath(All)` [C9]). Python then does three things on that small subgraph:

1. It enumerates simple paths of at most 6 hops.
2. It sums the band products per sanctioned owner and subject, applying the open and closed bound rule that PHASE-2.md 3.4 gives for products [K2]. The same rule holds for sums of positive terms: a sum reaches its bound only if every term does.
3. It runs the fixpoint: an entity is "at least" blocked when the minimum bounds of its blocked owners' direct shares sum to 50 or more, and "possibly" blocked when the maximum bounds do.

For exposure through control, re-run stage 1 with the controlled entities of stage 2 as start nodes (`UNWIND $seed_ids` and `MATCH (s:Entity {id: ...})` in place of the label scan).

Query `40_sanctions_owns_subgraph.cypher`:

```cypher
// sanctions_exposure, stage 1: every OWNS edge within max_prefix + 1 hops below a sanctioned legal entity,
// returned once each. ANY SHORTEST gives breadth-first reachability (one path per sanctioned entity and
// reached entity), so the number of rows grows with edges, not with paths. Python computes the
// effective share ranges (sum over simple paths of band products) and the OFAC-style blocked fixpoint.
// A quantifier upper bound of 0 is rejected, so max_prefix starts at 1 (max_hops 2 to 6).
// lint-values: max_prefix=1,2,3,4,5
MATCH (s:Sanctioned:LegalEntity)
MATCH ANY SHORTEST (s)-[:OWNS]->{0,{{max_prefix}}}(x:LegalEntity)
MATCH (x)-[o:OWNS]->(y:LegalEntity)
WITH DISTINCT o, x, y
RETURN o.id AS edge_id, x.id AS owner_id, y.id AS owned_id,
       o.share_pct_min AS share_min, o.share_pct_max AS share_max,
       coalesce(o.share_min_exclusive, false) AS min_open,
       coalesce(o.share_max_exclusive, false) AS max_open,
       x:Sanctioned AS owner_sanctioned
ORDER BY edge_id
LIMIT $limit;
```

Query `41_sanctions_control_links.cypher`:

```cypher
// sanctions_exposure, stage 2: control and directorship links from sanctioned legal entities
// (exposure without ownership). DIRECTOR_OF carries no share band, so its share columns are null.
MATCH (s:Sanctioned:LegalEntity)-[l:CONTROLS|DIRECTOR_OF]->(x:LegalEntity)
RETURN s.id AS sanctioned_id, type(l) AS link_type, l.id AS edge_id, x.id AS subject_id,
       l.share_pct_min AS share_min, l.share_pct_max AS share_max
ORDER BY sanctioned_id, subject_id, edge_id
LIMIT $limit;
```

Query `42_sanctions_details.cypher`:

```cypher
// sanctions_exposure, stage 3: the listing behind each sanctioned entity, for the explanation and for the
// "delisted party" look-alike (end_date in the past). Dates are ISO strings and may be partial.
UNWIND $entity_ids AS entity_id
MATCH (e:Entity {id: entity_id})-[:SUBJECT_OF]->(san:Sanction)
RETURN e.id AS entity_id, san.id AS sanction_id, san.authority AS authority, san.program AS program,
       san.listing_date AS listing_date, san.start_date AS start_date, san.end_date AS end_date
ORDER BY entity_id, sanction_id;
```

The same reachability idea in its simplest form (it lints for 1 to 6 hops):

Query `53_shortest_reachability_note.cypher`:

```cypher
// reachability without path enumeration: one breadth-first shortest path per reached node.
// lint-values: max_hops=1,2,3,4,5,6
MATCH (s:Entity {id: $start_id})
MATCH p = ANY SHORTEST (s)-[:OWNS|CONTROLS]->{1,{{max_hops}}}(x:LegalEntity)
RETURN x.id AS reached_id, length(p) AS hops
ORDER BY hops, reached_id
LIMIT $limit;
```

### 2.13 formation_agent_cluster

Pattern (7.2 item 11): one agent with `REPRESENTS` to many companies, or one formation agent's registered address. Incorporation dates come in bursts, nominee directors or secretaries are shared, and the companies pay each other [K1]. Python finds incorporation bursts from partial dates and directors shared across clients, and runs query 02 for payments within the cluster. The agent's own registered address joins this typology to 2.11.

Query `43_formation_agents.cypher`:

```cypher
// formation_agent_cluster, stage 1: agents with REPRESENTS edges to many companies
// (a relationship type scan, not a scan of every legal entity).
MATCH (agent:LegalEntity)-[:REPRESENTS]->(c:Company)
WITH agent, count(DISTINCT c) AS clients
WHERE clients >= $min_clients
RETURN agent.id AS agent_id, clients
ORDER BY clients DESC, agent_id
LIMIT $limit;
```

Query `44_formation_agent_clients.cypher`:

```cypher
// formation_agent_cluster, stage 2: each agent's client companies with incorporation date, registered
// addresses and directors. Python finds incorporation bursts and directors shared across clients.
UNWIND $agent_ids AS agent_id
MATCH (agent:Entity:LegalEntity {id: agent_id})-[:REPRESENTS]->(c:Company)
RETURN agent.id AS agent_id, c.id AS company_id, c.incorporation_date AS incorporation_date,
       c.jurisdiction AS jurisdiction,
       COLLECT { MATCH (c)-[h:HAS_ADDRESS]->(a:Address) WHERE h.role = 'registered'
                 RETURN a.id ORDER BY a.id } AS registered_address_ids,
       COLLECT { MATCH (d:LegalEntity)-[dr:DIRECTOR_OF]->(c)
                 RETURN {director_id: d.id, is_nominee: coalesce(dr.is_nominee, false),
                         role: dr.role, start_date: dr.start_date} AS item
                 ORDER BY item.director_id } AS directors
ORDER BY agent_id, company_id
LIMIT $limit;
```

### 2.14 recycled_directors

Pattern (7.2 item 12): a director with many `DIRECTOR_OF` edges, appointments that start and end in bursts, relatives of a controller as directors, and payments between companies that share the director [K1]. Python handles the date bursts and runs query 02 over the director's companies.

Query `45_recycled_directors.cypher`:

```cypher
// recycled_directors, stage 1: directors with many appointments. COUNT without a label on the far node
// is answered from the degree; DIRECTOR_OF always ends at an Organization in C2.
MATCH (d:LegalEntity)
WITH d, COUNT { (d)-[:DIRECTOR_OF]->() } AS appointments
WHERE appointments >= $min_appointments
RETURN d.id AS director_id, d:Person AS is_person, appointments
ORDER BY appointments DESC, director_id
LIMIT $limit;
```

Query `46_recycled_director_appointments.cypher`:

```cypher
// recycled_directors, stage 2: the appointments of each candidate, and whether the director is a relative
// of someone who owns or controls the same organisation. Python finds start and end bursts.
UNWIND $director_ids AS director_id
MATCH (d:Entity:LegalEntity {id: director_id})-[dr:DIRECTOR_OF]->(o:Organization)
RETURN d.id AS director_id, o.id AS organization_id, dr.id AS edge_id, dr.role AS role,
       coalesce(dr.is_nominee, false) AS is_nominee, dr.start_date AS start_date, dr.end_date AS end_date,
       EXISTS { (d)-[:FAMILY_OF]-(:Person)-[:OWNS|CONTROLS]->(o) } AS relative_of_owner_or_controller
ORDER BY director_id, organization_id, edge_id
LIMIT $limit;
```

### 2.15 pep_exposure

Pattern (7.2 item 13): paths of at most 4 hops from a `:PEP` or `:RCA` person through `FAMILY_OF`, `ASSOCIATE_OF`, `OWNS`, `CONTROLS` or `DIRECTOR_OF` to the subject [K1]. The inner predicate lets family and associate links run in either direction. Ownership, control and directorship must point away from the PEP. This is a pre-filter, so the breadth-first search never follows a wrong-way link [C1]. `ALL SHORTEST` returns every tied shortest path, which makes the result deterministic. Python keeps the smallest edge-id list per pair and applies the homonym and former-office look-alikes.

Query `47_pep_exposure.cypher`:

```cypher
// pep_exposure: all shortest paths of 1 to 4 hops from each PEP or RCA person to every reachable legal
// entity, through family and associates (either direction) or outward ownership, control and directorship.
// ALL SHORTEST (not SHORTEST 1) keeps the result deterministic; Python picks the smallest edge-id list.
MATCH (pep:PEP|RCA)
WHERE pep:Person
MATCH p = ALL SHORTEST (pep) ((x)-[l:FAMILY_OF|ASSOCIATE_OF|OWNS|CONTROLS|DIRECTOR_OF]-(y:LegalEntity)
              WHERE type(l) IN ['FAMILY_OF', 'ASSOCIATE_OF'] OR startNode(l) = x){1,4} (subject:LegalEntity)
WHERE subject <> pep
RETURN pep.id AS pep_id, pep:PEP AS is_pep, pep:RCA AS is_rca, subject.id AS subject_id,
       [n IN nodes(p) | n.id] AS node_ids, [r IN l | r.id] AS edge_ids, [r IN l | type(r)] AS link_types,
       length(p) AS hops
ORDER BY pep_id, hops, subject_id, edge_ids
LIMIT $limit;
```

### 2.16 cash_commingling

Pattern (7.2 item 14): a company account whose `cash_deposit` volume is far above peers in the same `sector`, deposited on days unrelated to trading, with outflows to owners or related parties [K1]. Robust peer statistics (median and median absolute deviation per sector and currency, including peers with no cash) belong in Python. Python also compares deposit days with the card activity pattern from query 03.

Query `48_cash_commingling_volume.cypher`:

```cypher
// cash_commingling, stage 1: cash deposit volume per company account in the window, with the sector.
// Python builds the sector and currency benchmark (median and median absolute deviation), including
// companies with no cash deposits (stage 1b), and flags accounts far above their peers.
MATCH (branch:Account)-[r:PAID]->(acct:Account)<-[:HOLDS_ACCOUNT]-(co:Company)
WHERE r.ts >= datetime($window_start) AND r.ts < datetime($window_end)
  AND r.channel = 'cash_deposit' AND branch.account_kind = 'cash_ledger'
WITH co, acct, r.currency AS currency, count(r) AS deposits, sum(r.amount) AS cash_total,
     count(DISTINCT date(r.ts)) AS deposit_days
RETURN co.id AS company_id, co.sector AS sector, acct.id AS account_id, currency,
       deposits, deposit_days, cash_total
ORDER BY sector, currency, company_id, account_id
LIMIT $limit;
```

Query `49_cash_commingling_peers.cypher`:

```cypher
// cash_commingling, stage 1b: number of companies with a customer account per sector (the peer base).
MATCH (co:Company)-[:HOLDS_ACCOUNT]->(acct:Account)
WHERE acct.account_kind = 'customer' AND co.sector IS NOT NULL
RETURN co.sector AS sector, count(DISTINCT co) AS companies
ORDER BY sector;
```

Query `50_cash_commingling_outflows.cypher`:

```cypher
// cash_commingling, stage 2: outflows of candidate accounts, marking payments to owners, controllers,
// directors and their relatives (related parties) rather than to suppliers and payroll.
UNWIND $account_ids AS account_id
MATCH (co:Company)-[:HOLDS_ACCOUNT]->(acct:Entity:Account {id: account_id})-[o:PAID]->(dst:Account)
WHERE o.ts >= datetime($window_start) AND o.ts < datetime($window_end)
OPTIONAL MATCH (rcv:LegalEntity)-[:HOLDS_ACCOUNT]->(dst)
RETURN acct.id AS account_id, co.id AS company_id, o.id AS edge_id, o.ts.epochMillis AS ts_ms,
       o.amount AS amount, o.currency AS currency, o.channel AS channel,
       dst.id AS counterparty_account_id, rcv.id AS counterparty_holder_id,
       rcv IS NOT NULL AND EXISTS { (rcv)-[:OWNS|CONTROLS|DIRECTOR_OF]->(co) } AS to_related_party,
       rcv IS NOT NULL AND EXISTS { (rcv)-[:FAMILY_OF]-(:Person)-[:OWNS|CONTROLS|DIRECTOR_OF]->(co) } AS to_relative
ORDER BY account_id, ts_ms, edge_id, counterparty_holder_id
LIMIT $limit;
```

### 2.17 Cypher or Python: the split

| Logic | Where | Why |
|---|---|---|
| Window seek, channel, kind and band filters, inline QPP pruning (window after the anchor, currency, amount band, hubs), simple-path checks, `EXISTS` and `COUNT` facts, ordered evidence lists | Cypher | Index use and pruning happen only in the database [C9][N3] |
| Strict time order of a found path | Cypher post-filter (cheap on short lists) or Python | No cross-iteration predicate in Cypher 5 [C1] |
| Sliding windows, UTC day buckets, daily totals, burst detection | Python | Variable windows per account are awkward in Cypher; integer `ts_ms` arithmetic is exact |
| Dwell times and first-in first-out matching of inflows to outflows | Python | Stateful matching; no stateful fold in 5.26 (`allReduce` is Cypher 25) [C12] |
| Sums and ratios of money | Python with `Decimal(str(amount)).quantize(Decimal("0.01"))` | `amount` is FLOAT [K1]; float sums depend on order; never sum across currencies |
| Gaps against partial dates (`opening_date`, `start_date`, `incorporation_date`) | Python | ISO strings may be `2019` or `2019-04`; string comparison in Cypher is wrong for them [K1] |
| Peer benchmarks (median, MAD), z-scores | Python | Grouping and re-joining is simpler and testable |
| Effective share ranges, open and closed bounds, the OFAC-style fixpoint | Python on the edge set from 2.12 | Sum over paths and fixpoint iteration; bound rules of PHASE-2.md 3.4 [K2] |
| Maximal chains, sub-chain and joint-holder dedupe, ring canonicalisation, `pattern_strength`, explanations, `alert_id` | Python | C4 rules live in Python (M1.9b) [K1] |

### 2.18 Pitfalls

1. **Cartesian products.** Comma-separated patterns or consecutive `MATCH` clauses with no shared variable multiply rows. None of the queries above has one. CI should fail on the server notification `03N90` (`CartesianProduct`) from `EXPLAIN` [N10] (5.4).
2. **Unbounded expansion.** Every quantifier has an upper bound: 8 hops at most, as PHASE-1.md requires [K1]. Every traversal is anchored on a seek or an id list, and pruned by an inline window. Hubs are excluded. Never use `+` or `*` quantifiers. The server warns `03N91` for unbounded shortest paths [N10].
3. **Duplicate paths.** Several cases repeat the same evidence:
   - chains found from later anchors are sub-chains;
   - joint accounts repeat structuring and same-holder cycle hits under each holder;
   - parallel payments give distinct cycles over the same accounts;
   - undirected patterns see each relationship once from each end (queries 26 and 18 handle this with `startNode()` and `s1.id < s2.id`).

   Python dedupes by sorted edge ids. The `OPTIONAL MATCH` of holders in 2.16 repeats a payment per holder, so group by `edge_id`.
4. **Direction.** Use the C2 directions of 2.1. Query `FAMILY_OF` and `ASSOCIATE_OF` undirected. Never count `CONSOLIDATES` as ownership. "Up" the ownership chain means following `OWNS` backwards [K2].
5. **Index-less id lookups.** `(a:Account {id: $id})` scans the label. Name `:Entity` [K1].
6. **Silent empty results.** These drop rows without an error:
   - A naive Python `datetime` parameter becomes a `LOCAL DATETIME`, and comparing it with `PAID.ts` gives `null` [D1][C7].
   - `NOT x IN $list` with `null` gives `null`.
   - A misspelled property is just `null`. The server warns `01N52` only for property names that exist nowhere in the database [N10].
7. **Durations.** Comparing durations returns `null` [C7]. `duration.between(...).days` drops months [C6].
8. **`SHORTEST 1` ties.** The pick among equal-length paths is not defined [C1]. Use `ALL SHORTEST` or `ORDER BY` and pick in Python.
9. **`LIMIT` without `ORDER BY`.** Which rows are cut is not defined. `ORDER BY` with `LIMIT` sorts the whole result first, so watch the timeout.
10. **Relationship uniqueness across clauses.** It is not enforced between `MATCH` clauses [C1]. The inline `t.ts > t0.ts` keeps the anchor out of the QPP.
11. **Currencies.** Group by `currency` before any sum. The GDS ring weight in 4.9 is only used by the optional Louvain step.
12. **Writes.** Detectors only read. GDS `write` mode is forbidden because it would add properties outside C2. Phase 1 decides that flags come only from source data [K1].

### 2.19 Lint results

- Query files: 43 files with 78 statements after expanding the `lint-values` variants, in the scratch folder `/tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/p3/research-cypher/queries/` [L1]. They are the blocks above plus the test helpers of 5.3 and 5.4.
- Project linter (`cypherlint/lint.mjs`, Cypher 5 rules, empty schema): "cypher-lint: 78 statements checked, 0 problems" [L1].
- Strict check (same splitting and expansion, plus a registry): "strict-lint: 78 statements checked, 0 problems" [L1]. The registry holds 405 functions and 701 procedures: built-ins and GDS from the language-support mock schema, and APOC limited to the 438 names annotated in APOC Core 5.26.32.
- Negative probe of 16 known-bad statements: the strict check reported all of them except `[*1..3]` and `ON ERROR RETRY`. The plain linter missed unknown functions, unknown `YIELD` columns and deprecated GDS procedures as well (table in 1.12) [L1].
- One lint finding changed a template: the sanctions query originally allowed a 0 upper bound for the prefix, which the linter rejects. The template now starts at 1.
- This note itself passes `tools/validate.py` (no dashes, every code block parses): its 44 Cypher blocks, the 43 files plus the pattern in 1.3, give 80 statements and 0 problems in both linters [L1].

## 3. Performance on a laptop graph (500,000 nodes, 2 million relationships)

### 3.1 Index use for PAID.ts

- C2 has the range index `paid_ts` on `PAID.ts` [K1].
- A pattern whose relationship is filtered by a range on `ts` can start from `DirectedRelationshipIndexSeekByRange` (or the undirected form). It "can be used for ... comparison operators such as <, >, <= and >=" [C9]. A relationship range index also returns rows in `ts` order, which can save a `Sort` [C10].
- The index serves only the relationship the plan seeks. Expanding from a bound node reads all of that node's `PAID` relationships of the right direction and filters `ts` afterwards. Neo4j has no per-node time index. Nodes with 50 or more relationships are "dense" and keep relationships grouped by type and direction (`db.relationship_grouping_threshold`, default 50) [O1].
- Hence the design: seek the anchor hop through the index, expand only within inline windows, and exclude hubs.
- If `EXPLAIN` shows a label scan instead of the seek, add `USING INDEX t0:PAID(ts)` [C10]. The server warns `01N31` when a hint cannot be fulfilled [N10]. Assert the operator in CI (5.4).
- `datetime($window_start)` is constant for the query, so it can be a seek bound. This is the normal planner rule (UNVERIFIED by a plan in this research).

### 3.2 What the planner does with quantified path patterns

- `Repeat(Trail)` runs QPPs that "cannot be solved (or solved efficiently) with the VarLengthExpand(All) operator". It takes one row and "repeatedly applies" the inner plan per the quantifier [C9].
- `TrailToVarExpandRewriter` turns a QPP into `VarLengthExpand` with inlined predicates when four conditions hold [N3]: the pattern has a single relationship; its node group variables are not used afterwards; its inner nodes are used only in predicates inside the QPP; and the quantifier fits an integer. The chain and cycle queries of section 2 return the `y` group variable, so they stay `Repeat(Trail)`.
- `MoveQuantifiedPathPatternPredicates` and `extractQPPPredicates` evaluate inner predicates per repetition. They push outer `all(x IN group WHERE ...)` predicates back into the inner plan, "much faster as it can potentially short-circuit the expansion" [N3]. Cross-iteration checks such as `t[i].ts < t[i + 1].ts` are not of that form and run after the path is built [N3].
- `SHORTEST` patterns run as `StatefulShortestPath(Into|All)` (BFS); predicates inside the pattern are pre-filters [C9][C1].
- Community runs the slotted runtime only. Pipelined and parallel are Enterprise [C11][O5]. Each query uses one thread.
- `COUNT {}` and `EXISTS {}` on bare one-hop patterns become degree lookups [N4]. `x IN $list` is a cached hash lookup [N5].
- Whether the degree rewrite also applies inside a QPP predicate: UNVERIFIED.

### 3.3 Memory settings

- Keep the Phase 1 standard profile: heap 2G (initial = max), page cache 2G, container limit 5g, `-XX:+ExitOnOutOfMemoryError`. For the small profile: heap 1G, page cache 512M, limit 2500m (PHASE-1.md M1.4) [K1].
- The manual says to "always define the page cache and heap size parameters explicitly". Size the page cache to the store plus native indexes, about times 1.2 [O2].
- Store size for this graph: a few hundred MB to about 1 GB with indexes (estimate, UNVERIFIED). Most of it is the 2 million `PAID` relationships with 8 to 9 properties each. Measure after a load with `du -sh` on the database folder or `neo4j-admin server memory-recommendation` [O2].
- Transaction memory [O1][O2][N7]:
  - `dbms.memory.transaction.total.max`: all transactions; default 70 percent of the heap; dynamic.
  - `db.memory.transaction.total.max`: per database; default 0, unlimited.
  - `db.memory.transaction.max`: per transaction; default 0, the largest possible.
- Recommendation: `NEO4J_db_memory_transaction_max=1G` with the 2G heap (512M in tests), so one runaway detector query fails instead of starving GDS or the API.
- The failure is `Neo.TransientError.General.MemoryPoolOutOfMemoryError` [N9]. Driver-managed transactions retry it (3.4).
- GDS keeps projected graphs and algorithm state on the heap ("The heap space is used for storing graph projections in the graph catalog, and algorithm state") [G2]. It checks estimated memory before running and refuses jobs that are "certain to not fit" [G12]. Native projections need a minimum page cache of about `8KB * 100 * readConcurrency` [G2].
- Page cache warm-up after restart "is available in Neo4j Enterprise Edition" [O1]. On Community the first run after a restart is cold, so never assert latency in CI.

### 3.4 Timeouts and retries from the Python driver 6

- `neo4j.Query(text, metadata=None, timeout=None)` sets "the transaction timeout in seconds"; the database terminates longer transactions. The setting overrides `db.transaction.timeout`, `0` means no limit, and `None` uses the server default [D1].
- `driver.execute_query(Query(...))` wraps the work with `unit_of_work(metadata, timeout)`, so the timeout applies there too [D1]. Phase 2 milestone 2.12 already uses `neo4j.Query(text, timeout=5.0)` [K2].
- On timeout the server raises `Neo.ClientError.Transaction.TransactionTimedOutClientConfiguration`, or `TransactionTimedOut` for the server default. Both are `ClientError`s, so nothing retries them [N9][D1]. Match `TransactionTimedOut` in the code, as milestone 2.12 does [K2].
- Retries: managed transactions (`execute_query`, `execute_read`) retry errors classed `TransientError` for up to `max_transaction_retry_time`, default 30 s [D1]. The memory-pool error is transient [N9]. "Auto-commit transactions (`Session.run`) are not retryable" [D1].
- For detectors use `session.run(Query(text, timeout=...), params)`: lazy, not retried, and failing fast.
- The server default `db.transaction.timeout` is 0. The 5.26 manual labels it Enterprise [O1]. The setting is defined in the Community configuration module, and a Community integration test expects it to terminate a transaction with `TransactionTimedOutClientConfiguration` [N7][N8]. NeonRadar does not need it.
- A running query can be listed with `SHOW TRANSACTIONS` and stopped with `TERMINATE TRANSACTIONS`; users can always end their own transactions [O4].
- GDS algorithms check a termination flag during computation (`terminationFlag.assertRunning()` in the K1 coloring loop) [G15]. So a transaction timeout also stops a GDS call (UNVERIFIED end to end).

```python
"""Run one detector query: auto-commit, lazy, never retried, bounded by a server-side timeout."""
from typing import LiteralString, cast

import neo4j
from neo4j import Query
from neo4j.exceptions import ClientError, TransientError

DETECT_TIMEOUT_S = 60.0


class DetectorQueryError(RuntimeError):
    pass


def stream_candidates(driver, text, params, timeout=DETECT_TIMEOUT_S):
    # text comes from a committed .cypher file, never from input; mypy needs the LiteralString cast.
    query = Query(cast(LiteralString, text), timeout=timeout)
    with driver.session(database="neo4j", default_access_mode=neo4j.READ_ACCESS, fetch_size=1000) as session:
        try:
            for record in session.run(query, params):
                yield record.data()
        except ClientError as exc:
            if "TransactionTimedOut" in (exc.code or ""):
                raise DetectorQueryError(f"timeout after {timeout} s") from exc
            raise
        except TransientError as exc:
            # For example Neo.TransientError.General.MemoryPoolOutOfMemoryError: fail, do not retry.
            raise DetectorQueryError(exc.code or "transient error") from exc
```

### 3.5 Streaming large results

- `execute_query()` "always retrieves all result records at once" [D2]. To stream, iterate the result of a session or transaction without turning it into a list [D2].
- The fetch size (driver default 1000) sets how many records the server sends before waiting [D1][D2]. A query with `ORDER BY` "requires the whole result set to be loaded into memory for sorting" before streaming starts [D2]. The candidate queries return one row per candidate with compact lists, so their results are small.
- The transaction stays open while Python reads a lazy result. Keep per-row Python work light, or read everything and then process, so the server-side timeout does not fire while Python is busy. That the timeout counts idle time is UNVERIFIED.
- `neo4j-rust-ext==6.4.1.0` is an optional faster drop-in for decoding (PHASE-2.md 3.1) [K2].

### 3.6 Realistic latency

There is no published Neo4j benchmark for this exact workload. The table gives order-of-magnitude expectations. Only the cited points are sourced; everything else is an estimate (UNVERIFIED).

| Work, page cache holding the store | Expected | Basis |
|---|---|---|
| Range seek of a 30-day window (about 150,000 `PAID` if the data spans a year) with filters and grouping | under 2 s | estimate |
| Anchored chain or cycle query with inline window, hub exclusion, 8 hops at most | seconds to tens of seconds | estimate. One published point: an exhaustive cycle search with per-step pruning over 10,000 accounts and 100,000 transactions took under 5 s on an AuraDB instance with 1 CPU and 1 GB. The older Neo4j 4 query (variable-length pattern, filters after expansion) took 5M ms, about 83 minutes; the article's text says almost 2 hours. The fast query used a model with transactions as nodes [P1] |
| The same traversal without anchoring or inline pruning | grows exponentially with hops and density | [C2] |
| Ownership and PEP traversals (bounded, BFS) | about a second per batch | Phase 2 target for ownership and paths: p95 under 2 s [K2]; estimate |
| GDS: Cypher projection and WCC of a candidate subgraph (up to about 100,000 relationships) | about a second or less | estimate |
| Container start with APOC and GDS | 20 to 60 s | estimate; the wait limit is 120 s [T1] |

Recommendation: add a benchmark command in Phase 3, modelled on the `bench queries` command of Phase 2 milestone 2.13 [K2]. It should time every detector stage on a generated 500,000 node and 2 million relationship graph and record p50, p95, rows, truncation and the hardware. Proposed budgets to confirm: each candidate query p95 under 30 s with a 30-day window, and a full `neonradar detect run` under 10 minutes.

## 4. GDS 2.13 Community

### 4.1 What Community Edition includes

- Neo4j 5.26.32 bundles GDS 2.13.14, and `NEO4J_PLUGINS` installs it from the image without a download [K3][K1].
- "The open source Community Edition" includes "all algorithms" [G1]. It limits:
  - catalog operations to managing graphs and models;
  - concurrency "to maximum 4 CPU cores";
  - the model catalog "to 3 models".
- Enterprise adds unlimited concurrency, backup and restore, Apache Arrow, persisted or shared models and an "optimized graph implementation" [G1].
- The default concurrency is 4 [G2].
- A request above the limit throws "Community users cannot exceed concurrency=4 (you configured concurrency=8)". This is `OpenGdsConcurrencyValidator`; the open pool size is 4 [G14]. That the Neo4j-built jar uses the same validator is expected but UNVERIFIED. Always pass `concurrency: 4` or less (PHASE-1.md 5.2) [K1].
- The production tier of 2.13 includes `wcc`, `scc`, `louvain`, `leiden`, `labelPropagation`, `degree`, `pageRank`, `articleRank`, `betweenness`, `closeness`, `eigenvector`, `nodeSimilarity`, `knn`, `kcore`, `triangleCount`, `localClusteringCoefficient`, `fastRP`, `bfs`, `dfs` and the shortest-path family [G13].

### 4.2 Projection

- Native projection [G3]:
  - `CALL gds.graph.project(graphName, nodeProjection, relationshipProjection, configuration) YIELD graphName, nodeProjection, nodeCount, relationshipProjection, relationshipCount, projectMillis`.
  - Configuration: `readConcurrency` (default 4), `nodeProperties`, `relationshipProperties`, `validateRelationships`, `jobId`.
  - Relationship projection keys: `type`, `orientation` (`NATURAL`, `UNDIRECTED`, `REVERSE`), `aggregation` (`NONE`, `SINGLE`, `COUNT`, `MIN`, `MAX`, `SUM`), `properties`.
  - It cannot filter by property, so it cannot select a time window.
- Cypher projection [G4]: an aggregation function, not a procedure.
  - `gds.graph.project(graphName, sourceNode, targetNode, dataConfig, configuration)` returns a map with `graphName`, `nodeCount`, `relationshipCount`, `projectMillis`, `query` and `configuration`.
  - `dataConfig`: `sourceNodeProperties`, `targetNodeProperties`, `sourceNodeLabels`, `targetNodeLabels`, `relationshipProperties`, `relationshipType`.
  - `configuration`: `readConcurrency` (default 4), `undirectedRelationshipTypes` (`['*']` for all), `inverseIndexedRelationshipTypes`.
  - Use it for windowed, filtered, pre-aggregated subgraphs. The docs note that the parallel runtime can speed it up, but that runtime is Enterprise only [G4].
- `gds.graph.project.cypher` (legacy) and its `.estimate` are deprecated in favour of the Cypher projection [G5]. The strict lint reports "Procedure gds.graph.project.cypher is deprecated" [L1].
- Drop: `CALL gds.graph.drop(graphName, failIfMissing, dbName, username) YIELD graphName, ...` with `failIfMissing` default true [G11]. Graphs live until dropped or until the database or DBMS stops [G3], so drop in a `finally` block.

### 4.3 Algorithm procedures (2.13.14)

Every listed algorithm has `stream`, `stats`, `mutate`, `write` and an `.estimate` for each mode. All take `(graphName, configuration)` [G6][G7][G8][G9][G10]. Common configuration: `nodeLabels`, `relationshipTypes`, `concurrency` (default 4), `jobId`, `logProgress` [G6]. The `YIELD` columns below match the 2.13 docs and the language-support registry [G6][G7][G9][G10][L1].

| Procedure | `stream` YIELD | Key configuration |
|---|---|---|
| `gds.wcc` | `nodeId, componentId` | `relationshipWeightProperty`, `threshold`, `seedProperty`, `consecutiveIds`, `minComponentSize` (stream) |
| `gds.louvain` | `nodeId, communityId, intermediateCommunityIds` | `relationshipWeightProperty`, `seedProperty`, `maxLevels` 10, `maxIterations` 10, `tolerance` 0.0001, `includeIntermediateCommunities`, `consecutiveIds`, `minCommunitySize` (stream) |
| `gds.labelPropagation` | `nodeId, communityId` | `maxIterations` 10, `nodeWeightProperty`, `relationshipWeightProperty`, `seedProperty`, `consecutiveIds`, `minCommunitySize` |
| `gds.degree` | `nodeId, score` | `orientation` (`NATURAL`, `REVERSE`, `UNDIRECTED`), `relationshipWeightProperty` |
| `gds.pageRank` | `nodeId, score` | `dampingFactor` 0.85, `maxIterations` 20, `tolerance` 1e-7, `relationshipWeightProperty`, `sourceNodes`, `scaler` |
| `gds.betweenness` | `nodeId, score` | `samplingSize`, `samplingSeed` |
| `gds.nodeSimilarity` | `node1, node2, similarity` | `similarityMetric` (`JACCARD`, `OVERLAP`, `COSINE`), `similarityCutoff`, `degreeCutoff`, `upperDegreeCutoff`, `topK` 10, `bottomK`, `topN`, `bottomN`, `relationshipWeightProperty`, `useComponents` |

- `stats` YIELD: for example `gds.wcc.stats` gives `componentCount, componentDistribution, preProcessingMillis, computeMillis, postProcessingMillis, configuration`.
- `mutate` and `write` add `mutateMillis` or `writeMillis` and `nodePropertiesWritten`. Node Similarity gives `nodesCompared, relationshipsWritten, similarityDistribution` instead.
- `.estimate` YIELD: `requiredMemory, treeView, mapView, bytesMin, bytesMax, nodeCount, relationshipCount, heapPercentageMin, heapPercentageMax` [G12].
- `gds.util.asNode(nodeId)` maps a GDS node id back to the database node. Return its C2 `id`.

### 4.4 Determinism

| Algorithm | Same result run to run? | What to do |
|---|---|---|
| WCC | The partition, yes. The ids, no: "The actual component ids may differ because the order of nodes projected in the in-memory graph is not guaranteed", and "due to the randomness in the Graph sampling optimization" [G6] | Name each component by its smallest C2 id |
| Louvain | Not guaranteed above concurrency 1. The 2.13.14 modularity optimisation colours nodes with a parallel greedy K1 colouring and applies community weight updates through atomic double arrays [G15]. There is no seed parameter [G7] | `concurrency: 1` (and `readConcurrency: 1` for the projection) in tests; canonicalise ids; assert relations, not ids. Determinism at concurrency 1 is expected from the code but UNVERIFIED by a run |
| Leiden | Needs an undirected graph, has a `theta` randomness parameter, and the examples pass `randomSeed` [G7] | Not recommended here; UNVERIFIED |
| Label Propagation | "Ties are broken arbitrarily but deterministically" [G8]; still depends on node order and iterations | Not recommended for alerts |
| KNN | `randomSeed`: "concurrency must be set to 1 when setting this parameter" [G10] | Not needed |
| Betweenness | Exact without sampling; with sampling, "using the same value will yield the same results between different runs" [G9] | Round scores |
| Degree, PageRank, Node Similarity | Deterministic for a given projected graph up to floating-point order (UNVERIFIED); stream output order is not defined | Round to 6 decimals; `ORDER BY` after `YIELD` |

### 4.5 Memory estimation

- Every mode has `.estimate`, which takes a graph name or a projection configuration. `gds.graph.project.estimate(nodeProjection, relationshipProjection, configuration)` also estimates a fictive graph with `nodeCount` and `relationshipCount` [G12].
- Every GDS procedure runs a heap check first. It "only blocks executions that are certain to not fit into memory", and `sudo: true` bypasses it [G12].
- For this project, run once in CI and record: `CALL gds.graph.project.estimate('*', '*', {nodeCount: 500000, relationshipCount: 2000000})`. It needs no data, so the figure is deterministic.

### 4.6 Running GDS from the Python driver

- GDS is ordinary Cypher: `CALL gds.<algo>.<mode>(...) YIELD ...` and the projection function, sent with `session.run` or `execute_read` (PHASE-1.md 3.2 already prefers this) [K1].
- Use a unique graph name per run (`nr-ring-<run_id>`), drop before and after, and never use managed-transaction retries for the projection: a retry after a partial success fails with "graph already exists".
- Projection and streaming are read queries. A detector never calls `write`. `mutate` changes only the in-memory graph.

```python
"""Mule ring step: project, run WCC, always drop; return rings as sorted tuples of C2 account ids."""
from neo4j import Query

DROP_GRAPH = "CALL gds.graph.drop($graph_name, false) YIELD graphName RETURN graphName"


def mule_rings(driver, run_id, collector_ids, window, project_ring, wcc_stream, min_size=4):
    params = {"graph_name": f"nr-ring-{run_id}", "collector_ids": sorted(collector_ids), **window}
    with driver.session(database="neo4j") as session:
        session.run(Query(DROP_GRAPH, timeout=30.0), params).consume()
        try:
            session.run(Query(project_ring, timeout=120.0), params).consume()
            rows = session.run(Query(wcc_stream, timeout=120.0), params).data()
        finally:
            session.run(Query(DROP_GRAPH, timeout=30.0), params).consume()
    members = {}
    for row in rows:
        members.setdefault(row["component_id"], []).append(row["account_id"])
    return sorted(tuple(sorted(group)) for group in members.values() if len(group) >= min_size)
```

### 4.7 The graphdatascience client

`graphdatascience` 2.2 (14 October 2026) is Apache-2.0 [D3]. It supports GDS from 2.13 (Phase 1 research) [K3]. It requires `pyarrow<26.0,>=21.0` and `pandas`, while Phase 2 pins `pyarrow>=26,<27` for Splink in the same `uv.lock` [D3][K2]. Adding it would break the lock, and plain `CALL` covers everything detectors need. Recommendation: do not add it.

### 4.8 Licence

- The neo4j/graph-data-science repository (OpenGDS) is under the GNU GPL version 3 (LICENSE.txt at 2.13.14). "The Neo4j Graph Data Science library as built and distributed by Neo4j includes the sources in this repository as well a suite of closed sources" and "is available to download and use under the constraints of its license" [G16].
- The GDS 2.13 manual calls Community Edition "open source" [G1]. A Neo4j staff answer of 2020 says "GDS uses the same GPL v3 license as the core database" [G17]. Neo4j's licensing page lists "Neo4j Community Edition (GPL v3)" and says nothing on GDS Community [G18].
- The licence text inside the jar that the image installs could not be read here (Maven Central and dist.neo4j.org are blocked): UNVERIFIED.
- What it means for NeonRadar (analysis, not legal advice; the tech lead and data steward should confirm):
  - GPLv3 obligations attach to conveying. "Mere interaction with a user through a computer network, with no transfer of a copy, is not conveying", and "You may make, run and propagate covered works that you do not convey, without conditions" (GPLv3 sections 0 and 2) [G16].
  - NeonRadar's Apache-2.0 code calls GDS procedures over Bolt in an official image the user pulls. It does not copy, link or ship GDS code, and the Cypher text is NeonRadar's own work. Inclusion of a covered work in an aggregate "does not cause this License to apply to the other parts of the aggregate" (section 5) [G16].
  - The Free Software Foundation's FAQ on programs that talk over sockets could not be fetched (gnu.org blocked): UNVERIFIED.
  - Obligations would arise if NeonRadar distributed an image, archive or appliance containing Neo4j or GDS jars. Then the GPL terms, and Neo4j's terms for the closed parts, apply to that distribution.
  - Recommendation: never vendor jars or publish a combined image. Keep `compose.yaml` pointing at `neo4j:5.26.32-community`, and list Neo4j Community (GPLv3), APOC Core (Apache-2.0) and GDS Community (GPLv3 per Neo4j's repository) as third-party runtime services in `NOTICE` or the README.

### 4.9 Recommendation for the mule-ring (fan-in ring) detector

- Use **WCC** on a **Cypher projection**:
  - payments in the window into the stage-1 fan-in candidates (2.7);
  - from customer accounts;
  - aggregated to one relationship per sender and collector pair;
  - projected as undirected.

  Each component is a set of collectors joined through shared senders, plus those senders: the "ring". Python keeps components with at least two collectors and `min_size` accounts.
- Why WCC: it is exact and deterministic as a partition, it has no tuning parameters, it is near-linear, it runs within the Community concurrency cap, and it explains in one sentence ("these accounts are linked by payments in the window") [G6].
- Why not Louvain or Leiden for alerts: Louvain optimises modularity, varies above concurrency 1 [G15], has no seed [G7], and gives groups that are hard to explain. Keep it only for the explainer, to split a very large component, with `concurrency: 1` (query below).
- Do not run WCC on all recent `PAID` edges. Background activity would likely join almost everything into one giant component (expected, UNVERIFIED for the generator's data), so filter to the candidates first.

Query `20_fan_in_ring_project.cypher`:

```cypher
// fan_in_collection ring variant, step 1: project payments in the window into the candidate collectors as
// an undirected, aggregated in-memory graph (one relationship per sender and collector pair).
// $graph_name is unique per run (for example "nr-ring-<run_id>"); Python drops it in a finally block.
UNWIND $collector_ids AS collector_id
MATCH (c:Entity:Account {id: collector_id})
MATCH (src:Account)-[r:PAID]->(c)
WHERE r.ts >= datetime($window_start) AND r.ts < datetime($window_end)
  AND src.account_kind = 'customer'
WITH src, c, count(r) AS payments, sum(r.amount) AS amount
WITH gds.graph.project($graph_name, src, c,
       {relationshipProperties: {payments: payments, amount: amount}},
       {undirectedRelationshipTypes: ['*'], readConcurrency: 4}) AS g
RETURN g.graphName AS graph_name, g.nodeCount AS node_count, g.relationshipCount AS relationship_count;
```

Query `21_fan_in_ring_wcc.cypher`:

```cypher
// fan_in_collection ring variant, step 2: weakly connected components of the projected graph.
// componentId values are not stable between runs; Python names each component by its smallest account id.
CALL gds.wcc.stream($graph_name, {concurrency: 4})
YIELD nodeId, componentId
RETURN gds.util.asNode(nodeId).id AS account_id, componentId AS component_id
ORDER BY component_id, account_id;
```

Query `22_fan_in_ring_estimate_and_drop.cypher`:

```cypher
// fan_in_collection ring variant: memory estimate before the run, and the drop that always follows it.
CALL gds.wcc.stream.estimate($graph_name, {concurrency: 4})
YIELD requiredMemory, bytesMax, nodeCount, relationshipCount
RETURN requiredMemory, bytesMax, nodeCount, relationshipCount;
CALL gds.graph.drop($graph_name, false)
YIELD graphName
RETURN graphName;
```

Query `23_fan_in_ring_louvain_optional.cypher`:

```cypher
// Optional, for the explainer only: Louvain splits a large component into denser groups. It runs with
// concurrency 1 so a test sees the same communities on every run; ids are still renamed in Python.
CALL gds.louvain.stream($graph_name, {concurrency: 1, maxLevels: 10, maxIterations: 10,
                                      tolerance: 0.0001, relationshipWeightProperty: 'amount'})
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).id AS account_id, communityId AS community_id
ORDER BY community_id, account_id;
```

Deterministic test for the ring detector:

- The fixture holds two rings, for example three collectors sharing eight mule senders, and two collectors with five. It also holds a charity collector with 30 unrelated donors (a look-alike) and background payments.
- `expected.json` lists the rings as sorted lists of account ids.
- The test runs the detector twice and asserts the same set of sorted tuples both times.
- It compares the GDS partition with a pure Python union-find over the rows of the projection's `MATCH` part (same parameters), so the oracle shares no code with GDS.
- It never compares `componentId` values, and it drops every graph between tests (query in 5.3).

```python
"""Oracle for the ring test: connected components of (sender, collector) pairs by union-find."""


def components(pairs):
    parent = {}

    def find(node):
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for left, right in pairs:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[max(root_left, root_right)] = min(root_left, root_right)
    groups = {}
    for node in parent:
        groups.setdefault(find(node), []).append(node)
    return sorted(tuple(sorted(group)) for group in groups.values())
```

## 5. Testing

### 5.1 Neo4j 5.26.32 with APOC and GDS in Testcontainers

- Import with `from testcontainers.community.neo4j import Neo4jContainer` (`testcontainers[neo4j]>=4.15,<5`, PHASE-1.md 3.1) [K1].
- In 4.15.0, `Neo4jContainer(image="neo4j:latest", port=7687, password=None, username=None)` [T1]:
  - sets `NEO4J_AUTH=neo4j/<password>`;
  - waits for the log line "Remote interface available at", then calls `driver.verify_connectivity()`;
  - offers `get_driver()`, plus `with_env`, `with_envs`, `with_kwargs` (passed to Docker, for example `mem_limit`) and `with_volume_mapping`.
- The image entrypoint behaves like this [T2]:
  - It installs each `NEO4J_PLUGINS` entry from the jar inside the image (`/var/lib/neo4j/labs/apoc-*-core.jar` and `/var/lib/neo4j/products/neo4j-graph-data-science-*.jar`).
  - It then adds `dbms.security.procedures.unrestricted=apoc.*`, and appends `gds.*` to the same line.
  - After that it writes `NEO4J_*` variables, and each one replaces any existing line for its setting. If you set `NEO4J_dbms_security_procedures_unrestricted`, list `apoc.*,gds.*` yourself.
  - Settings that start with `apoc.` go to `apoc.conf`.
- Allowlist: `dbms.security.procedures.allowlist` names the "procedures and functions that should be available from a library"; "no extensions other than those listed will be loaded". It concerns plugins, and its default `*` loads everything [O3]. GDS needs `gds.*` in any allowlist (Phase 1 research) [K3].
- A detector test container with `NEO4J_dbms_security_procedures_allowlist=gds.*` proves the detector queries use no APOC. Keep it separate from tests that need `apoc.meta.stats` (`neonradar graph stats`) [K1].
- The minimum password length is 8, so the default `password` works. Use a longer test password.

```python
"""conftest.py: one Neo4j 5.26.32 container with APOC and GDS per test session."""
import os

import pytest
from testcontainers.community.neo4j import Neo4jContainer

NEO4J_IMAGE = os.environ.get("NEO4J_TEST_IMAGE", "neo4j:5.26.32-community")


@pytest.fixture(scope="session")
def neo4j_container():
    container = (
        Neo4jContainer(image=NEO4J_IMAGE, password="nr-test-password-0001")
        .with_env("NEO4J_PLUGINS", '["apoc", "graph-data-science"]')
        .with_env("NEO4J_server_memory_heap_initial__size", "1G")
        .with_env("NEO4J_server_memory_heap_max__size", "1G")
        .with_env("NEO4J_server_memory_pagecache_size", "512M")
        .with_env("NEO4J_db_memory_transaction_max", "512M")
        .with_env("NEO4J_server_jvm_additional", "-XX:+ExitOnOutOfMemoryError")
        .with_kwargs(mem_limit="3g")
    )
    with container as started:
        yield started


@pytest.fixture(scope="session")
def neo4j_driver(neo4j_container):
    with neo4j_container.get_driver() as driver:
        driver.verify_connectivity()
        yield driver
```

Query `51_test_cleanup.cypher`:

```cypher
// tests: drop every in-memory graph left in the GDS catalog (run between test modules).
CALL gds.graph.list()
YIELD graphName
CALL gds.graph.drop(graphName, false)
YIELD graphName AS dropped
RETURN count(dropped) AS graphs_dropped;
```

Query `52_test_versions.cypher`:

```cypher
// tests: the server, APOC and GDS versions the run used (recorded in run.json).
CALL dbms.components()
YIELD name, versions, edition
RETURN name, versions, edition, apoc.version() AS apoc_version, gds.version() AS gds_version;
```

### 5.2 Startup time and GitHub Actions

- Startup wait limit: `TC_MAX_TRIES` (default 120) times `TC_POOLING_INTERVAL` (default 1 s) gives 120 s [T1]. Raise `TC_MAX_TRIES` in CI if needed.
- Startup time with both plugins: 20 to 60 s (estimate, UNVERIFIED). Measure it in CI and log it.
- Image: `neo4j:5.26.32-community` is 351,668,049 bytes compressed for amd64 (349,377,329 for arm64). The tag was re-pushed on 17 October 2026: the Phase 1 research saw a 12 October push [T3][K3].
- The tag moves when the base image is rebuilt. For reproducible CI, pin the index digest (`neo4j:5.26.32-community@sha256:0a6e7aedf54a531f76286032d4365ead65b11cca05e4a15cdf23b8e53d6db02b` on 18 October 2026) and bump it in reviewed pull requests [T3].
- Testcontainers also pulls `testcontainers/ryuk:0.8.1` [T1].
- GitHub-hosted `ubuntu-latest` (Ubuntu 24.04): 4 CPUs, 16 GB RAM and 14 GB SSD for public repositories; 2 CPUs, 8 GB RAM and 14 GB SSD for private ones [T4].
  - With 2 CPUs, GDS `concurrency: 4` still works but oversubscribes. WCC results do not depend on it.
  - Keep heap 1G and page cache 512M for fixtures.
  - Use one container per session (or one per `pytest-xdist` worker) and do not run tests in parallel against one database.

```yaml
# .github/workflows/ci.yml, integration job (sketch; the job id stays "integration" as in PHASE-1.md M1.6)
integration:
  runs-on: ubuntu-24.04
  timeout-minutes: 30
  env:
    NEO4J_TEST_IMAGE: "neo4j:5.26.32-community@sha256:0a6e7aedf54a531f76286032d4365ead65b11cca05e4a15cdf23b8e53d6db02b"
    TC_MAX_TRIES: "180"
  steps:
    - uses: actions/checkout@v7
    - uses: astral-sh/setup-uv@v10.3.0
    - run: docker pull "$NEO4J_TEST_IMAGE"
    - run: uv run pytest -m integration detect/tests
```

### 5.3 Deterministic assertions

- Each typology gets a handcrafted synthetic fixture with a known answer and an `expected.json`, as in M1.9b. The test asserts that the set of `tuple(sorted(alert["evidence"]["edge_ids"]))` equals the expected set exactly, and covers the look-alike cases that must not fire [K1].
- Run each detector twice in one test. The lists of `alert_id` must be equal; C4 derives the id from sorted evidence [K1].
- Fixed run parameters: the window comes from the test, never from the clock. The queries contain no `datetime()` without an argument.
- No `elementId()`, GDS node ids or `componentId` values in outputs or assertions. Rename communities by their smallest member id.
- Money as `Decimal` rounded to cents. Scores rounded before comparison (for example 6 decimals).
- Every Cypher result has an `ORDER BY` on C2 ids. Python sorts every set before output. No output depends on dict or set iteration order.
- Clean state: wipe the database between test modules (`CALL (n) { DETACH DELETE n } IN TRANSACTIONS` through `session.run`, PHASE-1.md 3.2) and drop all GDS graphs (query above) [K1].

### 5.4 Server-side checks in CI (EXPLAIN)

The offline linters cannot see the planner. So, against the test container, run `EXPLAIN` on every rendered detector query with real parameters. `01N60` is the server's warning for missing parameters [N10]. The test fails when any of these holds:

- `summary.query_type` is not `"r"` (read only) [D1].
- `summary.gql_status_objects` contains a status that starts with `01N` other than `01N50`, `01N51` or `01N52`. That family covers deprecations (`01N00` to `01N03`), unfulfillable hints (`01N30`, `01N31`), an unsupported runtime (`01N40`) and missing parameters (`01N60`). `01N50` to `01N52` are expected when a fixture lacks a label, type or property [N10].
- It contains `03N90` (cartesian product), `03N91` (unbounded shortest path), `03N92` (exhaustive shortest path) or `03N60` (subquery variable shadowing) [N10].
- For the anchored queries of 2.3 to 2.6, the plan does not contain `RelationshipIndexSeekByRange`.

The exact keys of the plan map are not documented in the Bolt message page (UNVERIFIED), so search the serialised plan.

```python
"""CI check: EXPLAIN every detector query against the test container."""
import json

ALLOWED_WARNINGS = {"01N50", "01N51", "01N52"}
FORBIDDEN = ("01N", "03N90", "03N91", "03N92", "03N60")


def explain_problems(driver, text, params, must_seek=False):
    _, summary, _ = driver.execute_query("EXPLAIN " + text, params, database_="neo4j")
    problems = []
    if summary.query_type != "r":
        problems.append(f"query type {summary.query_type}")
    for status in summary.gql_status_objects:
        code = status.gql_status
        if code.startswith(FORBIDDEN) and code not in ALLOWED_WARNINGS:
            problems.append(f"{code}: {status.status_description}")
    if must_seek and "RelationshipIndexSeekByRange" not in json.dumps(summary.plan):
        problems.append("no relationship index seek on PAID.ts")
    return problems
```

## 6. Neo4j 5.26 Community limits that affect the design

| Limit | Effect | Workaround |
|---|---|---|
| Only the slotted runtime; pipelined and parallel runtimes are Enterprise [O5][C11] | One thread per query; no `CYPHER runtime=parallel` | Run independent detectors in parallel Python threads, one session each, at most about the core count; keep queries anchored |
| No property existence, type or key constraints [O5] | Missing or mistyped properties read as `null` | Loader validation and invariant tests (PHASE-1.md 5.2, PHASE-2.md 5.2); `coalesce()` for optional flags such as `is_nominee` and the share flags [K1][K2] |
| No databases beyond `system` and the default one [O5] | No per-run or per-test database | One container per test session; `run_id` on alerts; Phase 2's separate real-data instance [K2] |
| No `query.log` (Enterprise) [O4] | No server-side slow-query log | Time queries in Python (`summary.result_available_after`, wall clock); `PROFILE` in development; `SHOW TRANSACTIONS` to inspect [O4] |
| No page-cache warm-up (Enterprise) [O1] | Cold first run after a restart | No latency assertions in CI; optional warm-up read before a benchmark |
| No role-based access control [O5] | No read-only role for the API or the copilot | Read access mode and `EXPLAIN` query-type checks (5.4) |
| `db.transaction.timeout` labelled Enterprise in the manual [O1] | Unclear server default | The driver's per-transaction `timeout` works on Community; the setting is in the Community code and tests [N7][N8] |
| GDS Community limits: concurrency 4, 3 models, no backup, no Arrow, no optimised graph implementation [G1] | More heap per projected graph; graphs lost on restart | Small, filtered projections; drop after use; re-project per run |
| No Cypher 25 [C3] | No `allReduce`, path modes or `coll.*` | Post-filters, list predicates, Python (sections 1 and 2) |
| No online backup [O5] | Evaluation snapshots need the server stopped | Rebuild from fixtures with the idempotent loader, or `neo4j-admin database dump` on a stopped server (Phase 2 research) [K2] |

## Sources

All checked on 18 October 2026. Repository facts were read from shallow clones at the commits given.

- [C1] Cypher 5 manual, Patterns: syntax and semantics. neo4j/docs-cypher, branch `cypher-5`, commit 3b2f6c2 (16 October 2026), `modules/ROOT/pages/patterns/reference.adoc`. https://neo4j.com/docs/cypher-manual/5/patterns/reference/
- [C2] Cypher 5 manual, Variable-length paths. Same commit, `patterns/variable-length-paths.adoc`. https://neo4j.com/docs/cypher-manual/5/patterns/variable-length-paths/
- [C3] Cypher 5 manual, Additions, deprecations, removals and compatibility. Same commit, `deprecations-additions-removals-compatibility.adoc` (sections for 5.3, 5.6, 5.9, 5.19, 5.21, 5.23, 5.24, 5.26, 2025.01 to 2026.08). https://neo4j.com/docs/cypher-manual/5/deprecations-additions-removals-compatibility/
- [C4] Cypher 5 manual, COUNT, COLLECT and EXISTS subqueries. Same commit, `subqueries/count.adoc`, `subqueries/collect.adoc`, `subqueries/existential.adoc`. https://neo4j.com/docs/cypher-manual/5/subqueries/
- [C5] Cypher 5 manual, CALL subqueries. Same commit, `subqueries/call-subquery.adoc`. https://neo4j.com/docs/cypher-manual/5/subqueries/call-subquery/
- [C6] Cypher 5 manual, temporal functions and values. Same commit, `functions/temporal/duration.adoc`, `functions/temporal/index.adoc`, `values-and-types/temporal.adoc`. https://neo4j.com/docs/cypher-manual/5/functions/temporal/duration/
- [C7] Cypher 5 manual, Equality, ordering and comparison of value types. Same commit, `values-and-types/ordering-equality-comparison.adoc`. https://neo4j.com/docs/cypher-manual/5/values-and-types/ordering-equality-comparison/
- [C8] Cypher 5 manual, ORDER BY. Same commit, `clauses/order-by.adoc`. https://neo4j.com/docs/cypher-manual/5/clauses/order-by/
- [C9] Cypher 5 manual, Operators in detail (`Repeat(Trail)`, `StatefulShortestPath(Into)`, `StatefulShortestPath(All)`, `DirectedRelationshipIndexSeekByRange`). Same commit, `planning-and-tuning/operators/operators-detail.adoc`. https://neo4j.com/docs/cypher-manual/5/planning-and-tuning/operators/operators-detail/
- [C10] Cypher 5 manual, indexes and index hints. Same commit, `indexes/performance-indexes/using-indexes.adoc`, `indexes/performance-indexes/index-hints.adoc`. https://neo4j.com/docs/cypher-manual/5/indexes/performance-indexes/using-indexes/
- [C11] Cypher 5 manual, Runtimes. Same commit, `planning-and-tuning/runtimes/concepts.adoc`. https://neo4j.com/docs/cypher-manual/5/planning-and-tuning/runtimes/concepts/
- [C12] Cypher 25 manual, predicate functions (`allReduce`) and variable-length paths. neo4j/docs-cypher, branch `cypher-25`, commit be8a5b7 (16 October 2026), `functions/predicate.adoc`, `patterns/variable-length-paths.adoc`. https://neo4j.com/docs/cypher-manual/25/functions/predicate/
- [C13] Cypher 25 manual, Match modes and path modes. Same commit, `patterns/reference/match-modes-and-path-modes.adoc`. https://neo4j.com/docs/cypher-manual/25/patterns/reference/match-modes-and-path-modes/
- [C14] Cypher 25 manual, additions by version and list functions. Same commit, `deprecations-additions-removals-compatibility.adoc`, `functions/list.adoc`. https://neo4j.com/docs/cypher-manual/25/deprecations-additions-removals-compatibility/
- [N1] Neo4j 5.26.32 source, neo4j/neo4j tag 5.26.32 (commit 27f2449), `community/cypher/front-end/ast/src/main/scala/org/neo4j/cypher/internal/ast/semantics/SemanticPatternCheck.scala` (`ensureNoReferencesOutFromPatternElement`). https://github.com/neo4j/neo4j/tree/5.26.32
- [N2] Same tag, `community/cypher/front-end/expressions/src/main/scala/org/neo4j/cypher/internal/expressions/Pattern.scala` (`NamedPatternPart.allVariables`).
- [N3] Same tag, `community/cypher/cypher-planner/src/main/scala/org/neo4j/cypher/internal/compiler/planner/logical/MoveQuantifiedPathPatternPredicates.scala`, `.../logical/idp/extractPredicates.scala` (`extractQPPPredicates`), `.../logical/convertToInlinedPredicates.scala`, `.../logical/plans/rewriter/TrailToVarExpandRewriter.scala`.
- [N4] Same tag, `.../planner/logical/steps/getDegreeRewriter.scala`.
- [N5] Same tag, `community/cypher/interpreted-runtime/src/main/scala/org/neo4j/cypher/internal/runtime/interpreted/commands/predicates/CachedIn.scala`, `community/values/src/main/java/org/neo4j/values/utils/InCache.java`.
- [N6] Same tag, `community/cypher/front-end/expressions/src/main/scala/org/neo4j/cypher/internal/expressions/functions/Function.scala` (built-in function list).
- [N7] Same tag, `community/configuration/src/main/java/org/neo4j/configuration/GraphDatabaseSettings.java` (`db.transaction.timeout`, `dbms.memory.transaction.total.max` at 70 percent of the heap, `db.memory.transaction.total.max`, `db.memory.transaction.max`).
- [N8] Same tag, `community/community-it/community-it/src/test/java/org/neo4j/server/TransactionTimeoutIT.java` (`shouldTimeoutAtDBMSLevel`).
- [N9] Same tag, `community/common/src/main/java/org/neo4j/kernel/api/exceptions/Status.java` (`TransactionTimedOut`, `TransactionTimedOutClientConfiguration` as ClientError; `General.MemoryPoolOutOfMemoryError` as TransientError).
- [N10] Same tag, `community/neo4j-notifications/src/main/java/org/neo4j/notifications/NotificationCodeWithDescription.java` (GQLSTATUS codes `01N00` to `01N03`, `01N30`, `01N31`, `01N40`, `01N50` to `01N52`, `01N60`, `03N60`, `03N90` to `03N92`).
- [O1] Operations Manual 5.26, Configuration settings. neo4j/docs-operations, branch `5.x`, commit 9fe3944 (9 October 2026, display version 5.26), `modules/ROOT/pages/configuration/configuration-settings.adoc`. https://neo4j.com/docs/operations-manual/5/configuration/configuration-settings/
- [O2] Operations Manual 5.26, Memory configuration. Same commit, `performance/memory-configuration.adoc`. https://neo4j.com/docs/operations-manual/5/performance/memory-configuration/
- [O3] Operations Manual 5.26, Securing extensions. Same commit, `security/securing-extensions.adoc`. https://neo4j.com/docs/operations-manual/5/security/securing-extensions/
- [O4] Operations Manual 5.26, Logging and Query management. Same commit, `monitoring/logging.adoc`, `monitoring/query-management.adoc`. https://neo4j.com/docs/operations-manual/5/monitoring/logging/
- [O5] Operations Manual 5.26, Introduction (edition table) and Store formats ("aligned is the default format for Community Edition"). Same commit, `introduction.adoc`, `database-internals/store-formats.adoc`. https://neo4j.com/docs/operations-manual/5/introduction/
- [G1] GDS 2.13 manual, Editions. neo4j/graph-data-science tag 2.13.14 (commit 417d7ec, 8 October 2026), `doc/modules/ROOT/partials/introduction/enterprise-features.adoc`. https://neo4j.com/docs/graph-data-science/2.13/introduction/
- [G2] GDS 2.13 manual, System requirements (heap, page cache, CPU and default concurrency). Same tag, `doc/modules/ROOT/pages/installation/System-requirements.adoc`. https://neo4j.com/docs/graph-data-science/2.13/installation/System-requirements/
- [G3] GDS 2.13 manual, Native projection. Same tag, `pages/management-ops/graph-creation/graph-project.adoc`. https://neo4j.com/docs/graph-data-science/2.13/management-ops/graph-creation/graph-project/
- [G4] GDS 2.13 manual, Cypher projection. Same tag, `pages/management-ops/graph-creation/graph-project-cypher-projection.adoc`. https://neo4j.com/docs/graph-data-science/2.13/management-ops/graph-creation/graph-project-cypher-projection/
- [G5] GDS 2.13 manual, Cypher projection (deprecated) and the graph operations reference. Same tag, `pages/management-ops/graph-creation/graph-project-cypher-legacy.adoc`, `pages/operations-reference/graph-operation-references.adoc`.
- [G6] GDS 2.13 manual, Weakly Connected Components and its configuration partials. Same tag, `pages/algorithms/wcc.adoc`, `partials/algorithms/wcc/`, `partials/algorithms/common-configuration/`. https://neo4j.com/docs/graph-data-science/2.13/algorithms/wcc/
- [G7] GDS 2.13 manual, Louvain and Leiden. Same tag, `pages/algorithms/louvain.adoc`, `pages/algorithms/leiden.adoc`, `partials/algorithms/louvain/`, `partials/algorithms/leiden/`. https://neo4j.com/docs/graph-data-science/2.13/algorithms/louvain/
- [G8] GDS 2.13 manual, Label Propagation. Same tag, `pages/algorithms/label-propagation.adoc`, `partials/algorithms/label-propagation/`.
- [G9] GDS 2.13 manual, Degree Centrality, PageRank and Betweenness Centrality. Same tag, `pages/algorithms/degree-centrality.adoc`, `page-rank.adoc`, `betweenness-centrality.adoc` and their partials.
- [G10] GDS 2.13 manual, Node Similarity and K-Nearest Neighbors. Same tag, `pages/algorithms/node-similarity.adoc`, `pages/algorithms/knn.adoc`, `partials/algorithms/node-similarity/`, `partials/algorithms/knn/knn-specific-algo-config.adoc`.
- [G11] GDS 2.13 manual, Dropping graphs. Same tag, `pages/management-ops/graph-drop.adoc`.
- [G12] GDS 2.13 manual, Memory estimation. Same tag, `pages/common-usage/memory-estimation.adoc`. https://neo4j.com/docs/graph-data-science/2.13/common-usage/memory-estimation/
- [G13] GDS 2.13 manual, Algorithm reference (tiers). Same tag, `pages/operations-reference/algorithm-references.adoc`.
- [G14] GDS 2.13.14 source, `concurrency-validation-api/src/main/java/org/neo4j/gds/concurrency/OpenGdsConcurrencyValidator.java` and `OpenGdsPoolSizes.java`.
- [G15] GDS 2.13.14 source, `algo/src/main/java/org/neo4j/gds/k1coloring/K1Coloring.java` and `algo/src/main/java/org/neo4j/gds/modularityoptimization/ModularityOptimization.java`.
- [G16] GDS 2.13.14 `README.adoc` (OpenGDS, the closed-source build) and `LICENSE.txt` (GNU GPL version 3, sections 0, 2 and 5 quoted).
- [G17] Neo4j community forum, "License model of GDS", Neo4j staff answer of 18 August 2020. https://community.neo4j.com/t/license-model-of-gds/23664/3
- [G18] Neo4j licensing page. https://neo4j.com/licensing/
- [A1] APOC Core, neo4j/apoc tag 5.26.32 (commit fc74597, 22 September 2026), `core/src/main/java` (235 functions, 11 aggregation functions and 192 procedures from the `@UserFunction`, `@UserAggregationFunction` and `@Procedure` annotations). https://github.com/neo4j/apoc/tree/5.26.32
- [A2] APOC Extended, neo4j-contrib/neo4j-apoc-procedures branch 5.26 (commit 27b2418, 6 August 2026), `extended/src/main/java/apoc/agg/`, `apoc/coll/CollExtended.java`, `apoc/temporal/TemporalExtended.java`, `apoc/algo/PathFindingExtended.java`. https://github.com/neo4j-contrib/neo4j-apoc-procedures/tree/5.26
- [A3] APOC manual, Deprecations and additions (APOC 2025.07 and 2025.11, deprecated in Cypher 25, with replacements). https://neo4j.com/docs/apoc/current/deprecations-and-additions/
- [D1] Neo4j Python driver 6.4.1, neo4j/neo4j-python-driver tag 6.4.1 (commit 9755761): `src/neo4j/_work/query.py` (`Query`, `unit_of_work`), `src/neo4j/_sync/driver.py` (`execute_query`), `src/neo4j/exceptions.py` (`TransientError` retryable; auto-commit not retryable), `src/neo4j/_conf.py` (`max_transaction_retry_time` 30.0, `fetch_size` 1000), `src/neo4j/_work/summary.py` (`plan`, `query_type`, `gql_status_objects`), `src/neo4j/_codec/hydration/bolt/v2/temporal.py` (naive datetime sent as local). https://github.com/neo4j/neo4j-python-driver/tree/6.4.1
- [D2] Neo4j Python driver manual 6.x, neo4j/docs-drivers branch `6.x` (commit a64c13f): `python-manual/modules/ROOT/pages/performance.adoc`, `query-advanced.adoc`, `data-types.adoc`. https://neo4j.com/docs/python-manual/current/performance/
- [D3] PyPI JSON API: https://pypi.org/pypi/graphdatascience/json (2.2, 14 October 2026, Apache-2.0, `pyarrow<26.0,>=21.0`), https://pypi.org/pypi/neo4j/json (6.4.1), https://pypi.org/pypi/testcontainers/json (4.15.0), https://pypi.org/pypi/neo4j-rust-ext/json (6.4.1.0)
- [T1] testcontainers-python tag testcontainers-v4.15.0 (commit 04267b3): `src/testcontainers/community/neo4j/__init__.py`, `src/testcontainers/core/config.py` (`TC_MAX_TRIES` 120, `TC_POOLING_INTERVAL` 1, `testcontainers/ryuk:0.8.1`), `src/testcontainers/core/container.py`. https://github.com/testcontainers/testcontainers-python/tree/testcontainers-v4.15.0
- [T2] neo4j/docker-neo4j (commit fd9e4ec, 30 September 2026): `docker-image-src/5/coredb/docker-entrypoint.sh` (`install_neo4j_plugins`, `apply_plugin_default_configuration`, `add_env_setting_to_conf`) and `neo4j-plugins.json`. https://github.com/neo4j/docker-neo4j
- [T3] Docker Hub API, tag `neo4j:5.26.32-community` (sizes, digests, last pushed 17 October 2026). https://hub.docker.com/v2/repositories/library/neo4j/tags/5.26.32-community
- [T4] GitHub Docs, GitHub-hosted runners. https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- [P1] Neo4j developer blog, "Did you take the Neo4j 5 Cypher bullet train?" (22 September 2023). https://neo4j.com/blog/developer/neo4j-5-cypher-bullet-train/
- [P2] Tutorial repository linked from [P1], commit 66e4d17, `queries/fraud_detection_with_neo4j.md`. https://github.com/halftermeyer/fraud-detection-training
- [K1] NeonRadar PHASE-1.md: sections 3.1, 3.2, 5.1 (channels and account kinds), 5.2 (C2 schema, migration 0001, Cypher conventions), 5.4 (C4), M1.4, M1.6, M1.9b, 7.2. `/home/claude/neonradar-phase1/doc/PHASE-1.md`
- [K2] NeonRadar PHASE-2.md: sections 3.1, 3.2, 3.4, 5.2 (C2 1.1.0), 5.3, milestones 2.12 and 2.13, section 8. `/home/claude/neonradar-phase2/doc/PHASE-2.md`
- [K3] NeonRadar Phase 1 research note `neo4j.md`, sections 2, 3 and 9. `/home/claude/neonradar-phase1/research/neo4j.md`
- [L1] Lint runs on this machine, 18 October 2026:
  - `node /tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/cypherlint/lint.mjs /tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/p3/research-cypher/queries` printed "cypher-lint: 78 statements checked, 0 problems".
  - `node /tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/p3/research-cypher/tools/strictlint.mjs /tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/p3/research-cypher/queries` printed "strict-lint: 78 statements checked, 0 problems".
  - The negative probe `/tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/p3/research-cypher/negative/bad.cypher` gave 22 problems (strict) and 15 problems (plain) on 16 statements.
  - The behaviour probes are in `/tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/p3/research-cypher/probe/`.
  - `python3 /home/claude/neonradar-phase3/tools/validate.py /home/claude/neonradar-phase3/research/detection-cypher-gds.md` printed "cypher-lint: 80 statements checked, 0 problems" and "OK". The strict check on the extracted blocks printed "strict-lint: 80 statements checked, 0 problems".
