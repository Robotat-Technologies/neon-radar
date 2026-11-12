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

## D3: General investigation teaching queries

Contributed by @amalika1922022-gif.

Examples 1–5 use the synthetic [C2 demo graph](../../contracts/C2-graph-schema.md).
Examples 6–11 use the separate [onboarding fixture](../../data/fixtures/onboarding/companies-20.csv).
Their labels and relationships are not interchangeable.
All examples are general, read-only and bounded; they are teaching queries, not approved detectors.
Thresholds are illustrative. Matches do not establish wrongdoing, common ownership or account balances.
Observed results below were checked in Neo4j Browser on 2026-11-11, except example 4 on 2026-11-12.
They apply to the locally loaded fixtures; other datasets may return different results, including zero rows.
The onboarding checker runs the `## @handle` sections below, not these teaching examples.

### 1. Incoming payment followed by a near-equal outgoing payment

Which accounts receive a payment, then send 90–100% of its amount to a different account within 24 hours in the same currency?

```cypher
MATCH path =
  (sender:Account)-[incoming:PAID]->
  (transit:Account)-[outgoing:PAID]->
  (recipient:Account)
WHERE sender.synthetic = true
  AND transit.synthetic = true
  AND recipient.synthetic = true
  AND incoming.synthetic = true
  AND outgoing.synthetic = true
  AND sender <> transit
  AND transit <> recipient
  AND sender <> recipient
  AND incoming.currency = outgoing.currency
  AND incoming.amount > 0
  AND outgoing.ts > incoming.ts
  AND outgoing.ts <= incoming.ts + duration('PT24H')
  AND outgoing.amount >= incoming.amount * 0.9
  AND outgoing.amount <= incoming.amount
RETURN path,
       incoming.amount AS incoming_amount,
       outgoing.amount AS outgoing_amount,
       incoming.currency AS currency,
       duration.between(incoming.ts, outgoing.ts) AS elapsed
ORDER BY incoming.ts, incoming.id, outgoing.id
LIMIT 25
```

**Observed result:** Two paths: GBP 2285.38 → 2172.14 in PT11M52S; EUR 103753.63 → 101668.18 in PT18H45M9S. Graph: six accounts, four payments.

**Use and limits:** Compares payment pairs, not total flows or residual balances. The three accounts differ; matching payments need not represent the same funds. One payment can appear in several paths.

**Sources:** [Explainer](../typologies/rapid-pass-through.md) · [Definition](../../detect/typologies/rapid_pass_through.yaml).

### 2. Multiple sending accounts paying one account (fan-in)

Which accounts receive positive payments from at least three distinct accounts on one UTC calendar day, in one currency?

```cypher
MATCH (sender:Account)-[payment:PAID]->(collector:Account)
WHERE sender.synthetic = true
  AND collector.synthetic = true
  AND payment.synthetic = true
  AND sender <> collector
  AND payment.amount > 0
  AND payment.currency IS NOT NULL
  AND payment.ts IS NOT NULL
WITH collector,
     date(payment.ts) AS payment_day,
     payment.currency AS currency,
     count(DISTINCT sender) AS sender_count,
     count(payment) AS payment_count,
     sum(payment.amount) AS total_received
WHERE sender_count >= 3
RETURN collector.id AS collector_id,
       collector.caption AS collector,
       payment_day,
       currency,
       sender_count,
       payment_count,
       total_received
ORDER BY sender_count DESC,
         collector_id,
         payment_day,
         currency
LIMIT 25
```

**Observed result:** One row: `syn-acct-0026` (`NRSYN0000000026`), 2026-04-02, GBP, three senders, three payments, total 46796.46.

**Use and limits:** Groups by collector, day and currency. A calendar day is not a rolling 24-hour window; distinct accounts need not have distinct holders. It does not examine subsequent outflows.

**Sources:** [Explainer](../typologies/fan-in-collection.md) · [Definition](../../detect/typologies/fan_in_collection.yaml).

### 3. One account paying multiple recipient accounts (fan-out)

Which accounts pay at least three distinct recipient accounts on one UTC calendar day, in one currency?

```cypher
MATCH (sender:Account)-[payment:PAID]->(recipient:Account)
WHERE sender.synthetic = true
  AND recipient.synthetic = true
  AND payment.synthetic = true
  AND sender <> recipient
  AND payment.amount > 0
  AND payment.currency IS NOT NULL
  AND payment.ts IS NOT NULL
WITH sender,
     date(payment.ts) AS payment_day,
     payment.currency AS currency,
     count(DISTINCT recipient) AS recipient_count,
     count(payment) AS payment_count,
     round(sum(payment.amount), 2) AS total_sent
WHERE recipient_count >= 3
RETURN sender.id AS sender_id,
       sender.caption AS sender,
       payment_day,
       currency,
       recipient_count,
       payment_count,
       total_sent
ORDER BY recipient_count DESC,
         sender_id,
         payment_day,
         currency
LIMIT 25
```

**Observed result:** Nine groups from three sending accounts; the final query rounds totals to two decimal places for display. All rows use GBP.

| sender_id | payment_day | recipients | payments | total_sent |
|---|---|---:|---:|---:|
| syn-acct-0020 | 2026-01-30 | 5 | 5 | 17155.14 |
| syn-acct-0021 | 2026-01-30 | 5 | 5 | 13109.14 |
| syn-acct-0014 | 2026-01-30 | 4 | 4 | 15239.13 |
| syn-acct-0014 | 2026-02-27 | 4 | 4 | 15239.13 |
| syn-acct-0014 | 2026-03-31 | 4 | 4 | 15239.13 |
| syn-acct-0020 | 2026-02-27 | 4 | 4 | 13881.57 |
| syn-acct-0020 | 2026-03-31 | 4 | 4 | 13881.57 |
| syn-acct-0021 | 2026-02-27 | 4 | 4 | 10823.76 |
| syn-acct-0021 | 2026-03-31 | 4 | 4 | 10823.76 |

**Use and limits:** Groups by sender, day and currency, not unique sender alone. Calendar days are not rolling windows. Recipient accounts need not have different holders; recurring payments may be legitimate payroll.

**Sources:** [Explainer](../typologies/fan-out-distribution.md) · [Definition](../../detect/typologies/fan_out_distribution.yaml).

### 4. Three-payment chains through distinct accounts

Which three-payment paths traverse four distinct accounts chronologically, in one currency, within 24 hours?

```cypher
MATCH path =
  (a:Account)-[first:PAID]->
  (b:Account)-[second:PAID]->
  (c:Account)-[third:PAID]->
  (d:Account)
WHERE all(n IN nodes(path) WHERE n.synthetic = true)
  AND all(r IN relationships(path)
          WHERE r.synthetic = true AND r.amount > 0)
  AND all(n IN nodes(path)
          WHERE single(other IN nodes(path) WHERE other = n))
  AND first.currency = second.currency
  AND second.currency = third.currency
  AND first.ts < second.ts
  AND second.ts < third.ts
  AND third.ts <= first.ts + duration('PT24H')
RETURN path,
       [n IN nodes(path) | n.id] AS account_ids,
       [r IN relationships(path) | r.amount] AS amounts,
       first.currency AS currency,
       duration.between(first.ts, third.ts) AS elapsed
ORDER BY first.ts, first.id, second.id, third.id
LIMIT 25
```

**Observed result:** Two paths (account IDs and amounts follow path order), both GBP:

| account_ids | amounts | elapsed |
|---|---|---|
| syn-acct-0021 → syn-acct-0001 → syn-acct-0020 → syn-acct-0026 | 2285.38 → 2172.14 → 3273.57 | PT3H35M46S |
| syn-acct-0010 → syn-acct-0020 → syn-acct-0030 → syn-acct-0026 | 6606.09 → 3256.84 → 36.81 | PT7H41M4S |

Combined graph: six accounts and six payments. Paths share accounts but use distinct payments.

**Use and limits:** Chronology does not trace the same funds or require similar amounts. The second path includes “Salary February 2026” and “Card purchase”; connectivity alone does not establish layering. Paths may overlap.

**Sources:** [Explainer](../typologies/layering-chain.md) · [Definition](../../detect/typologies/layering_chain.yaml).

### 5. Company pairs sharing a director and an address

Which company pairs share both a recorded director and the same address node?

```cypher
MATCH (director:LegalEntity)-[role1:DIRECTOR_OF]->
      (first:Company)-[address1:HAS_ADDRESS]->
      (address:Address)<-[address2:HAS_ADDRESS]-
      (second:Company)<-[role2:DIRECTOR_OF]-(director)
WHERE first.id < second.id
  AND all(n IN [director, first, second, address]
          WHERE n.synthetic = true)
  AND all(r IN [role1, role2, address1, address2]
          WHERE r.synthetic = true)
RETURN DISTINCT
       director.id AS director_id,
       director.caption AS director,
       first.id AS first_company_id,
       first.caption AS first_company,
       second.id AS second_company_id,
       second.caption AS second_company,
       address.id AS address_id,
       address.full AS shared_address
ORDER BY director_id,
         first_company_id,
         second_company_id,
         address_id
LIMIT 25
```

**Observed result:** Ten unordered pairs among `syn-co-0001`, `syn-co-0002`, `syn-co-0005`, `syn-co-0006` and `syn-co-0007` (five companies, not ten). All share Hilary Akhtar (`syn-p-0022`) and Suite 6, 167 Ploverleat Yard, Bristol (`syn-addr-0001`).

**Use and limits:** Compares IDs to avoid reversed pairs and uses DISTINCT for identical output rows. Does not check date overlap. HAS_ADDRESS is not necessarily a registered office; inspect its role. LegalEntity directors may be people or organisations. Equivalent text on separate address nodes will not match.

**Sources:** [C2 schema](../../contracts/C2-graph-schema.md).

### 6. Companies sharing a direct parent

Which company pairs have the same direct parent?

```cypher
MATCH (first:OnbCompany)<-[:PARENT_OF]-
      (parent:OnbCompany)-[:PARENT_OF]->
      (second:OnbCompany)
WHERE first.id < second.id
RETURN parent.name AS parent_company,
       first.name AS first_subsidiary,
       second.name AS second_subsidiary
ORDER BY parent_company, first_subsidiary, second_subsidiary
LIMIT 25
```

**Observed result:** Zero rows: the fixture has a parent–child–grandchild chain, but no parent with two direct subsidiaries.

**Use and limits:** Two hops through a shared parent; comparing IDs excludes self-pairs and reversed pairs. Onboarding PARENT_OF does not establish ownership percentages.

### 7. Directors of companies at shared registered addresses

Who directs companies at addresses shared by at least two companies?

```cypher
MATCH (company:OnbCompany)-[:REGISTERED_AT]->
      (address:OnbAddress)
WITH address, count(DISTINCT company) AS company_count
WHERE company_count >= 2
MATCH (director:OnbPerson)-[:DIRECTS]->
      (company:OnbCompany)-[:REGISTERED_AT]->(address)
RETURN DISTINCT address.full AS shared_address,
                company_count,
                director.id AS director_id,
                director.name AS director
ORDER BY shared_address, director_id
LIMIT 25
```

**Observed result:** Four rows at Suite 5, 40 Example Street, Exampleton, QE1 4AB, United Kingdom; company_count is 5 in every row: Hollis Wrenford (`onb-p-03`), Noor Saltash (`onb-p-05`), Vera Pellingham (`onb-p-07`), Galina Stormcrest (`onb-p-12`).

**Use and limits:** Counts companies per address, then follows DIRECTS and REGISTERED_AT. company_count is the address total, not each director’s company count. Shared addresses do not establish that directors know each other.

### 8. Direct and indirect subsidiaries within two hops

Which companies have subsidiaries reachable through one or two parent relationships?

```cypher
MATCH path =
  (parent:OnbCompany)-[:PARENT_OF]->{1,2}
  (subsidiary:OnbCompany)
RETURN parent.id AS parent_id,
       parent.name AS parent_company,
       subsidiary.id AS subsidiary_id,
       subsidiary.name AS subsidiary,
       length(path) AS hops
ORDER BY parent_id, hops, subsidiary_id
LIMIT 25
```

**Observed result:** Three rows: `onb-co-01` → `onb-co-02` (1 hop); `onb-co-01` → `onb-co-03` (2 hops); `onb-co-02` → `onb-co-03` (1 hop).

**Use and limits:** length(path) reports depth. Stops after two hops; does not identify ultimate beneficial owners or ownership percentages.

### 9. Directors of direct subsidiaries

Who directs each direct subsidiary, and which company is its parent?

```cypher
MATCH path =
  (parent:OnbCompany)-[:PARENT_OF]->
  (subsidiary:OnbCompany)<-[:DIRECTS]-
  (director:OnbPerson)
RETURN path
ORDER BY parent.id, subsidiary.id, director.id
LIMIT 25
```

**Observed result:** Two paths: Holdings → Logistics ← Tobias Fenmarch; Logistics → Freight ← Samira Oakhollow (all companies are Lattice Orchard). Combined graph: three companies, two people, four relationships.

**Use and limits:** Two hops from parent through subsidiary to director; RETURN path enables graph display. Does not imply the director also directs or owns the parent.

### 10. Company pairs sharing an address but having different directors

Which company pairs share a registered address and have a pair of different recorded directors?

```cypher
MATCH (first:OnbCompany)-[:REGISTERED_AT]->
      (address:OnbAddress)<-[:REGISTERED_AT]-
      (second:OnbCompany),
      (first)<-[:DIRECTS]-(director1:OnbPerson),
      (second)<-[:DIRECTS]-(director2:OnbPerson)
WHERE first.id < second.id
  AND director1 <> director2
RETURN first.name AS first_company,
       director1.name AS first_director,
       second.name AS second_company,
       director2.name AS second_director,
       address.full AS shared_address
ORDER BY first_company, second_company
LIMIT 25
```

**Observed result:** Nine rows among the five companies at Suite 5, 40 Example Street, Exampleton, QE1 4AB, United Kingdom. Copperfen Analytics Ltd / Quartzfield Bakery Ltd is excluded because both have Hollis Wrenford as director.

**Use and limits:** Compares company IDs to avoid reversed pairs. With multiple directors, a matching pair does not prove the companies have no other director in common.

### 11. Directors of multiple companies and their address counts

Which directors have more than one matched company, and how many distinct registered address nodes do those companies use?

```cypher
MATCH (director:OnbPerson)-[:DIRECTS]->
      (company:OnbCompany)-[:REGISTERED_AT]->
      (address:OnbAddress)
WITH director,
     count(DISTINCT company) AS company_count,
     count(DISTINCT address) AS address_count
WHERE company_count > 1
RETURN director.name AS director,
       company_count,
       address_count
ORDER BY company_count DESC, director
LIMIT 25
```

**Observed result:** Four rows (companies / addresses): Philippa Marrowby 3 / 3; Hollis Wrenford 2 / 1; Samira Oakhollow 2 / 2; Tobias Fenmarch 2 / 2.

**Use and limits:** Two hops from director through company to address. Counts distinct nodes; companies lacking REGISTERED_AT are excluded. Address counts do not independently verify physical locations.

## Assignment 1 contributions

The sections below retain the one-query-per-person format described above.

## @example

```cypher
MATCH (c:OnbCompany {id: 'onb-co-04'})-[:REGISTERED_AT]->(a:OnbAddress)<-[:REGISTERED_AT]-(other:OnbCompany)
RETURN other.id AS company_id, other.name AS company, a.full AS shared_address
ORDER BY company_id
LIMIT 25
```

Finds every company that shares a registered address with Copperfen Analytics Ltd (`onb-co-04`). Companies are not linked to each other directly, so the path needs two hops: from the company out to its address, and from the address back to the other companies registered there.

## @abdullah-ald

```cypher
MATCH (first:OnbCompany)<-[:DIRECTS]-(director:OnbPerson)-[:DIRECTS]->(second:OnbCompany)
WHERE first.id < second.id
RETURN director.name AS director, first.name AS first_company, first.jurisdiction AS first_jurisdiction,
       second.name AS second_company, second.jurisdiction AS second_jurisdiction
ORDER BY director, first_company, second_company
LIMIT 25
```

Finds pairs of companies that have the same recorded director, including each company's recorded jurisdiction. The pattern needs two hops because it goes from the first company to the director and then from that director to the second company. Comparing the company ids keeps each pair once instead of returning it again in the opposite order.
