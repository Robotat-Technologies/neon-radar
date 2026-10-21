# Assignment 1: load a CSV, write a two-hop query, open a pull request

| | |
|---|---|
| Who | Everyone on the team, no exceptions |
| Due | Friday 23 October 2026 (`schedule.assignment_1_due` in [project.yaml](../build/project.yaml)). Dates are a plan, not a deadline the build enforces ([OD-1](../build/operator-decisions.md)); the project lead confirms the date or moves it. |
| You hand in | One pull request that adds your section to [first-queries.md](first-queries.md) |
| AI help | Allowed. The pull request and the explanation are yours: be ready to explain every line. |

The point is not the query. The point is that everyone on the team has one merged pull request with their name on it early, before the project gets hard ([project plan](../plan/neonradar-project-plan.md), "Next steps"). On the way you load data into Neo4j, write your first traversal and go through review once.

## Before you start

Get the local stack running, as described in [local-stack.md](../architecture/local-stack.md):

```bash
make setup      # Python packages, pre-commit hooks, .env with a generated Neo4j password
make plugins    # once, with network: the Neo4j image and the pinned GDS jar
make up         # starts Neo4j and waits until it is healthy
make smoke      # prints the Neo4j, APOC and GDS versions
```

If any of these fails, `uv run neonradar doctor` shows what is missing, and the table at the end of local-stack.md lists the usual fixes. Ask your mentor early rather than late.

## 1. Copy the CSV into the import folder

```bash
cp data/fixtures/onboarding/companies-20.csv data/import/
```

Neo4j reads files only from its import folder. Compose mounts `data/import/` read-only at `/import` inside the container, so the file appears there at once. Git ignores everything in `data/import/` except `.gitkeep`, so the copy never ends up in a commit; the committed original stays in `data/fixtures/onboarding/`.

Every company, person and address in the file is invented. The first column, `synthetic`, says so on every row. The names were checked against the public Companies House search so that none of them matches a real company or officer exactly (operator decision OD-12).

## 2. Open Neo4j Browser

Open <http://localhost:7474> and connect to `neo4j://localhost:7687` as user `neo4j` with the `NEO4J_PASSWORD` from your `.env` ([local-stack.md](../architecture/local-stack.md), "Neo4j Browser").

## 3. Look at the data before you load it

```cypher
LOAD CSV WITH HEADERS FROM 'file:///companies-20.csv' AS row
RETURN row LIMIT 5
```

Each row is one company with its director, its registered address and, for some companies, the id of its parent company. `LOAD CSV` hands you every value as a string, and an empty field as `null`.

## 4. Load it into the onboarding model

Build exactly this model, so that your graph matches the one the check builds (step 7):

| Label | Key (use it in `MERGE`) | Properties, from the columns |
|---|---|---|
| `OnbCompany` | `id` | `id` (`company_id`), `name` (`company_name`), `jurisdiction`, `incorporated_on` (a date: `date(...)`), `synthetic` (a boolean: `toBoolean(...)`) |
| `OnbPerson` | `id` | `id` (`director_id`), `name` (`director_name`), `synthetic` |
| `OnbAddress` | `full` | `full` (`registered_address`), `synthetic` |

| Relationship | From and to | Meaning |
|---|---|---|
| `DIRECTS` | `OnbPerson` to `OnbCompany` | the person is a director of the company |
| `REGISTERED_AT` | `OnbCompany` to `OnbAddress` | the company's registered address |
| `PARENT_OF` | `OnbCompany` to `OnbCompany` | the company in `parent_company_id` is the parent of the company in `company_id` |

These labels are deliberately separate from the real graph schema (contract C2, with labels such as `Company`, `Person` and `Address`). Use them only for onboarding.

Write the load yourself first. Some things to think about:

- `MERGE` on the key, not `CREATE`, so that running your load twice changes nothing. Several rows name the same person or the same address; with `MERGE` they become one node.
- A parent company can appear later in the file than its child, so add `PARENT_OF` in a second pass, once every company exists.
- `incorporated_on` arrives as a string. Store it as a date so that comparisons such as `c.incorporated_on < date('2018-01-01')` work.

<details>
<summary>Reference load (open it after you have tried)</summary>

Paste both statements into Browser; it runs statements separated by semicolons one after the other.

```cypher
// Reference load for Assignment 1: the same graph as `neonradar onboarding check` builds
LOAD CSV WITH HEADERS FROM 'file:///companies-20.csv' AS row
MERGE (c:OnbCompany {id: row.company_id})
SET c.name = row.company_name, c.jurisdiction = row.jurisdiction,
    c.incorporated_on = date(row.incorporated_on), c.synthetic = toBoolean(row.synthetic)
MERGE (p:OnbPerson {id: row.director_id})
SET p.name = row.director_name, p.synthetic = toBoolean(row.synthetic)
MERGE (a:OnbAddress {full: row.registered_address})
SET a.synthetic = toBoolean(row.synthetic)
MERGE (p)-[:DIRECTS]->(c)
MERGE (c)-[:REGISTERED_AT]->(a);

LOAD CSV WITH HEADERS FROM 'file:///companies-20.csv' AS row
WITH row WHERE row.parent_company_id IS NOT NULL
MATCH (child:OnbCompany {id: row.company_id})
MATCH (parent:OnbCompany {id: row.parent_company_id})
MERGE (parent)-[:PARENT_OF]->(child);
```

</details>

## 5. Check what you loaded

```cypher
MATCH (n) WHERE n:OnbCompany OR n:OnbPerson OR n:OnbAddress
RETURN labels(n)[0] AS label, count(*) AS nodes ORDER BY label
```

Expect `OnbAddress` 16, `OnbCompany` 20 and `OnbPerson` 15.

```cypher
MATCH ()-[r:DIRECTS|REGISTERED_AT|PARENT_OF]->()
RETURN type(r) AS type, count(*) AS relationships ORDER BY type
```

Expect `DIRECTS` 20, `PARENT_OF` 2 and `REGISTERED_AT` 20.

More than that means a load used `CREATE`, or other property names. `uv run neonradar onboarding reset` removes every `Onb*` node and its relationships, and nothing else; then load again.

## 6. Write your query

Your query traverses at least two hops: its pattern goes through at least two relationships, for example `(a)-[:R1]->(b)<-[:R2]-(c)`. The data was built so that some two-hop questions have interesting answers: some people direct more than one company, several companies share one registered address, and three companies form a parent chain. Questions you could ask (or ask your own; do not copy `@example`):

- Which pairs of companies share a director?
- Which company sits two levels below another in the parent chain?
- Who directs the companies registered at the shared address?
- Which people direct companies in more than one jurisdiction?

Things that catch people out:

- The direction of an arrow matters. `(p)-[:DIRECTS]->(c)` and `(c)-[:DIRECTS]->(p)` are different questions, and the second finds nothing.
- A symmetric pattern such as `(a)<-[:DIRECTS]-(p)-[:DIRECTS]->(b)` returns every pair twice, as `(a, b)` and `(b, a)`. `WHERE a.id < b.id` keeps one.
- `DISTINCT` removes repeated rows when two paths lead to the same answer.
- `ORDER BY` makes the output the same every time, which makes it easier to review.
- Bound it: fixed hops or `{1,3}`, never `[*]`, and end with `LIMIT`. Every query in the project is bounded ([.claude/rules/cypher.md](../../.claude/rules/cypher.md)).
- Use literal values such as `'onb-co-04'`; the check passes no parameters. (In project code it is the other way round: always parameters.)
- No `LOAD CSV`, `apoc.` or `CALL` in your first query. Every first query runs on everyone's machine, so the check refuses these without running them: a `LOAD CSV FROM 'https://...'` would make an outbound request from each of them.

## 7. Add your query and run the check

Add your section to [first-queries.md](first-queries.md), in the format that file describes: `## @your-handle`, one `cypher` block, and two or three lines on what the query finds and why it needs two hops. Then, from the repository root:

```bash
make onboarding-check
```

It loads the onboarding data with a reference loader (with `MERGE`, so it changes nothing when your load followed the model), runs every query in `first-queries.md` read-only with a 10-second timeout, and prints one line per handle, `OK` with the number of rows or `FAIL` with the error. It exits 1 when any query fails. Your line must say `OK`.

## 8. Open a pull request

```bash
git switch -c assignment-1/<your-handle>
git add docs/team/first-queries.md
git commit -m "docs(docs): add the first query of @<your-handle>"
git push -u origin assignment-1/<your-handle>
gh pr create --web
```

- **Title:** Conventional Commits, which CI checks, for example `docs(docs): add my first query (@your-handle)`.
- **Body:** fill in the [pull request template](../../.github/pull_request_template.md). Summary: what your query finds. Milestone: Assignment 1. Human owner: you. Acceptance evidence: your line from `make onboarding-check`. Contract impact: none. Data and licence impact: no data files added. AI involvement: say honestly whether and how you used AI.
- **Label:** `learning`. If you cannot add labels, your reviewer adds it.
- **Commit only `first-queries.md`.** Not the CSV copy (git ignores it anyway), not anything from `data/`.
- If the project lead opened an issue "Assignment 1: @your-handle" for you, write `Closes #<number>` in the body.

## 9. Be ready to explain every line

A reviewer from another squad reads your pull request ([CONTRIBUTING.md](../../CONTRIBUTING.md)). They may ask:

- What does each line of your query do? What changes if you reverse one arrow?
- Why does it need two hops, and what does the node in the middle stand for?
- Could it return the same row twice? How do you know?
- Why does the load use `MERGE` and not `CREATE`? What happens when it runs twice?
- Why does the load convert `incorporated_on` with `date()`?

"The AI wrote it" is not an answer. If you cannot explain a line yet, that is fine: find out, and write down what confused you in your learning log.

**For reviewers.** Besides "can the author explain every line", check that the query only reads, is bounded (fixed hops or a bounded range, and a `LIMIT`), uses literal values, and uses no `LOAD CSV`, `apoc.*` (for example `apoc.load.*`) or `CALL`. `make onboarding-check` refuses the last three, but read the query anyway: it runs on every teammate's machine once it is merged. The text under the query describes a structure, not a judgement about the companies or people.

## Afterwards

- Start your learning log: [docs/learning/README.md](../learning/README.md) explains how. This assignment is a good first entry. You write it yourself; no agent writes it for you.
- `uv run neonradar onboarding reset` removes the `Onb*` nodes when you no longer want them. (`make reset CONFIRM=yes` deletes the whole local database, not just the onboarding data.)

## When something goes wrong

| Symptom | What to do |
|---|---|
| `Couldn't load the external resource at: file:///companies-20.csv` | The file is not in `data/import/`, or its name differs: repeat step 1 |
| Browser or the check says the password is wrong (`Unauthorized`) | See "Stop, reset and passwords" in [local-stack.md](../architecture/local-stack.md) |
| `FAIL  NEO4J_PASSWORD is not set` | Run the check from the repository root after `make up`, which creates `.env` |
| `FAIL  @you  Neo.ClientError.Statement.AccessMode: ...` | Your query writes (`CREATE`, `MERGE`, `SET`, `DELETE`); first queries only read |
| `FAIL  @you  Neo.ClientError.Statement.ParameterMissing: ...` | Replace each `$parameter` with a literal value |
| `FAIL  @you  Neo.ClientError.Transaction.TransactionTimedOut...` | The query ran for more than 10 seconds: bound it with fewer hops or a `LIMIT` |
| `FAIL  @you  format: ...` | Your section does not follow the format in [first-queries.md](first-queries.md) |
| `FAIL  @you  not allowed: first queries may not use LOAD CSV, apoc. or CALL` | Remove the `LOAD CSV`, `apoc.` or `CALL` (also `CALL { }` subqueries, and the word "call" in a comment or string); answer the question with plain `MATCH` patterns |
| Your counts in step 5 are higher than expected, or the check prints `WARN` | `uv run neonradar onboarding reset`, then load again |
