# First queries

Every person on the team adds one Cypher query here as part of [Assignment 1](assignment-1.md). The query runs against the onboarding data (the `OnbCompany`, `OnbPerson` and `OnbAddress` labels built from [companies-20.csv](../../data/fixtures/onboarding/companies-20.csv)) and traverses at least two hops.

## Format

- One section per person, headed `## @your-github-handle`.
- Exactly one fenced code block marked `cypher` in your section, holding one statement.
- Under the block, two or three lines: what the query finds, and why it needs two hops.
- Add your section in alphabetical order of handle, after `## @example`. Sorted sections touch different lines, so parallel pull requests rarely conflict; if yours does, merge `main` into your branch and keep both sections.

`make onboarding-check` (or `uv run neonradar onboarding check`) loads the onboarding data and runs every section's query. Your query passes when it:

- reads only: the check runs it in a read transaction, and the server refuses any write;
- finishes within 10 seconds;
- uses literal values, not parameters such as `$id` (the check passes none). In project code every query takes parameters and bounds its traversals and results ([.claude/rules/cypher.md](../../.claude/rules/cypher.md)); first queries use literals only because the check passes none;
- is bounded: a fixed number of hops or a bounded range such as `{1,3}`, never `[*]`, and it ends with `LIMIT`;
- does not use `LOAD CSV`, `apoc.` procedures or functions, or `CALL` (including `CALL { }` subqueries). The check refuses them without running the query: first queries run on everyone's machine, and a `LOAD CSV FROM 'https://...'` would make an outbound request from each of them;
- is a single statement (one trailing semicolon is fine).

The check prints one line per handle: `OK` with the number of rows returned, or `FAIL` with the error. Text in this file outside the `## @handle` sections, like this format guide, is not checked.

When you describe what your query finds, describe the structure, not a judgement about the companies or people: "shares a registered address with four other companies", not a label for what they might be. The data is invented, but the habit is the one this project needs ([README](../../README.md), the standing disclaimer).

## @example

```cypher
MATCH (c:OnbCompany {id: 'onb-co-04'})-[:REGISTERED_AT]->(a:OnbAddress)<-[:REGISTERED_AT]-(other:OnbCompany)
RETURN other.id AS company_id, other.name AS company, a.full AS shared_address
ORDER BY company_id
LIMIT 25
```

Finds every company that shares a registered address with Copperfen Analytics Ltd (`onb-co-04`). Companies are not linked to each other directly, so the path needs two hops: from the company out to its address, and from the address back to the other companies registered there.
