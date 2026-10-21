# 0009. Alert object and wording

- **Status:** proposed
- **Date:** 2026-10-21
- **Deciders:** @robotat-com (tech lead, typology researchers)

## Context

Every detector produces alerts, the API serves them, the UI lists and explains them, and from Phase 4 the copilot answers questions about them (`docs/build/PHASE-1.md` 4.1). Detection, copilot and UI squads build in parallel, so the alert needs one agreed shape, frozen at Gate 1 with the other contracts (5.0, 5.4).

NeonRadar is an educational reference project for anti-money-laundering and anti-corruption work. It runs on synthetic data and, next to it, on public registers that name real people and companies. Two guardrails shape the alert (2.1):

- G1: no real person or company is ever labelled suspicious. Planted scenarios run only among synthetic entities; real entities receive synthetic background activity at most.
- G5: text about entities describes structures and patterns and never accuses anyone.

An alert is also a claim about data that a reader must be able to check. Public graph tools word their disclaimers the same way: legitimate uses exist, a match or an inclusion does not imply wrongdoing, and identity and data errors happen and can be corrected [icij_faq] [opensanctions_glossary] [opencorporates_terms] [openownership_register_terms] (quotes in `docs/research/2026-10-16/aml-domain.md` section 4). Their safeguards are words on a page; the alert itself has to carry the same caution in its fields and its wording.

## Options considered

1. **A closed alert object with reproducible evidence, deterministic ids, a `pattern_strength` and two wording classes enforced by a lint (chosen).** Every alert carries the C2 ids of its evidence nodes and relationships and the Cypher query with parameters that finds them again, so a reviewer re-runs the query instead of trusting the alert. The id is a hash of the typology, the detector version and the sorted evidence ids, so a re-run yields the same alerts and the loader can merge on them. The model refuses an alert that contradicts its own data flags. Drawbacks: detectors must collect evidence ids and the reproduction query; text must come from templates and pass a lint, which makes some phrasings impossible.
2. **Free-text alerts with a risk score.** The easiest to build. A score labelled "risk" or "suspicion" reads as a judgement about the entity, which G1 and G5 rule out, and free text cannot be checked mechanically.
3. **Detectors write only graph labels or properties on entities (for example a flag on a node).** Simple for queries, but it turns a detection into a property of the entity, mixes NeonRadar's output with source data (C2 says flags come only from source data), and loses the evidence and the reason.

## Decision

We will use the C4 Alert object as defined in `contracts/C4-alert.md` (version 1.0.0):

- **Evidence that reproduces the finding:** `evidence.node_ids` and `evidence.edge_ids` in C2 form, the query and its parameters, and an optional time window. Findings are checked, not trusted.
- **Deterministic ids:** `alert_id` is `alr-` plus the first 20 hex characters of SHA-1 over the typology, the detector version and the sorted evidence ids. The model recomputes it.
- **`pattern_strength`, never a risk or suspicion score:** a number from 0 to 1 for how closely the evidence matches the typology's graph pattern, used only to order the queue (`priority`).
- **Two wording classes:** `synthetic_scenario` only when every evidence node, subject and evidence-account holder is synthetic; `structural_pattern` otherwise. Headlines come from the typology's two templates (`detect/typologies/<slug>.yaml`), chosen by the class.
- **A wording lint:** the forbidden patterns of `PHASE-1.md` 7.1, kept in `contracts/wording/forbidden-terms.txt`, checked in the alert model (headline), in headline rendering, in CI (`scripts/check_wording.py`) and in the contract tests. The three disclaimers are kept verbatim in `contracts/wording/`, and every alert names the standing disclaimer.

A reference project for anti-corruption work must never accuse anyone by accident, so these rules are enforced by code rather than left to reviewers.

## Consequences

- Detectors must return evidence ids and a reproduction query, and compute the data flags with one helper (M1.9b); the model rejects an alert whose id, flags or wording class disagree with its own ids and dataset list.
- Re-running a detector on the same graph produces the same alert ids; a new detector version produces new ids, which keeps old and new results apart.
- The UI and the copilot can word every alert from its fields: "synthetic scenario" only for all-synthetic alerts, "structural pattern" next to any real entity, and the synthetic-activity flag for patterns that lie in generated background activity.
- Some phrasings are impossible by design. A typology that needs a word on the forbidden list in its headline has to describe the structure instead; the list itself is a contract file, so changing it is a contract change after the freeze.
- The lint is a word list, not an understanding of meaning: it catches accusatory vocabulary, not every misleading sentence. Human review of templates and explainers stays necessary.
- The disclaimers are verbatim texts; changing them goes through `contracts/CHANGELOG.md` like any contract change.

## Sources

- `docs/build/PHASE-1.md` sections 2.1 (G1, G5), 4.1, 5.0, 5.4, 5.5 and 7.1.
- `docs/research/2026-10-16/aml-domain.md` section 4 (how public graph tools word their disclaimers, with the quotes).
- [icij_faq] Offshore Leaks Database: frequently asked questions. ICIJ, living page. https://offshoreleaks.icij.org/pages/faq
- [opensanctions_glossary] OpenSanctions glossary. OpenSanctions, living page. https://www.opensanctions.org/docs/glossary
- [opencorporates_terms] OpenCorporates terms of use. OpenCorporates, living page. https://opencorporates.com/terms-of-use-2/
- [openownership_register_terms] Open Ownership Register terms and conditions (archived page: the register closed on 29 November 2024). Open Ownership, 2024. https://register.openownership.org/terms-and-conditions
- `contracts/C4-alert.md` and `contracts/CHANGELOG.md` (1.0.0, C4).
- `docs/build/operator-decisions.md` OD-11 (id form) and OD-12 (synthetic names checked against the Companies House register).
