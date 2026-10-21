# Assignment 2: check one typology explainer against its sources

| | |
|---|---|
| Who | One person per typology. The project lead fills in the Assignee column of the [table below](#the-15-typologies) |
| Due | Tuesday 27 October 2026 (`schedule.assignment_2_due` in [project.yaml](../build/project.yaml)). Dates are a plan, not a deadline the build enforces ([OD-1](../build/operator-decisions.md)); the project lead confirms the date or moves it. |
| You hand in | One pull request, under your own name, that corrects your typology's explainer and definition file |
| AI help | Allowed. The pull request and the explanation are yours: be ready to explain every change. |

An agent drafted all fifteen typology explainers in [docs/typologies/](../typologies/README.md) and their definition files in `detect/typologies/` (milestones M1.10b-1 to M1.10b-3). Every draft is `status: draft`. Your job is to take one of them, read the primary sources it cites, and check the draft sentence by sentence against what those sources actually say. Fix what is wrong, add what is missing with citations, and submit the result as your own work.

Why it matters: "Nobody can write a detection query for a pattern they cannot describe in a paragraph" ([project plan](../plan/neonradar-project-plan.md), "Assignment 2"). Phase 3 builds a detector for a typology only after a typology researcher has approved it, and Gate 1 needs `circular_flow` approved ([PHASE-1.md](../build/PHASE-1.md), M1.10b). Your check is what a researcher reads before approving. On the way you learn one money laundering pattern well enough to explain it to the team.

## The 15 typologies

The list is section 7.2 of [PHASE-1.md](../build/PHASE-1.md). "Research note" is the lettered entry in section 2 of the [AML domain research note](../research/2026-10-16/aml-domain.md), a map of the sources with short quotes. It is not a source itself: check every statement against the primary source. "Sources to read" is the definition file's `citations` list as merged on 21 October 2026; if the definition file changes, it is the current list. Each key's title, link and notes are in the [bibliography](../sources/bibliography.yaml).

| # | Typology id (slug) | Name (explainer) | Definition file | Tier | Research note | Sources to read | Assignee |
|---|---|---|---|---|---|---|---|
| 1 | `structuring` | [Structuring (smurfing) below reporting thresholds](../typologies/structuring.md) | [structuring.yaml](../../detect/typologies/structuring.yaml) | core | (a) | `cfr_31_1010_314`, `ffiec_appendix_g`, `ffiec_appendix_f`, `fatf_pml_2018`, `fincen_fin_2014_a005`, `fincen_fin_2025_a003`, `europol_efecta_2023` | |
| 2 | `rapid_pass_through` | [Rapid pass-through (funnel or transit accounts)](../typologies/rapid-pass-through.md) | [rapid_pass_through.yaml](../../detect/typologies/rapid_pass_through.yaml) | core | (b) | `fincen_fin_2014_a005`, `fatf_egmont_tbml_indicators_2021`, `fatf_cyber_fraud_2023`, `ffiec_appendix_f`, `fatf_egmont_concealment_2018` | |
| 3 | `layering_chain` | [Layering through chains of transfers](../typologies/layering-chain.md) | [layering_chain.yaml](../../detect/typologies/layering_chain.yaml) | core | (c) | `fatf_faq`, `fatf_pml_2018`, `fatf_egmont_concealment_2018`, `fincen_fin_2006_g014`, `europol_efecta_2023`, `wolfsberg_payment_transparency_2023`, `ffiec_appendix_f` | |
| 4 | `circular_flow` | [Round-tripping or circular flows](../typologies/circular-flow.md) | [circular_flow.yaml](../../detect/typologies/circular_flow.yaml) | core | (d) | `fatf_egmont_tbml_indicators_2021`, `fatf_egmont_concealment_2018`, `ffiec_appendix_f`, `fatf_pml_2018` | |
| 5 | `fan_in_collection` | [Fan-in to a collection account](../typologies/fan-in-collection.md) | [fan_in_collection.yaml](../../detect/typologies/fan_in_collection.yaml) | core | (e) | `fatf_cyber_fraud_2023`, `fincen_fin_2025_a003`, `fincen_fin_2014_a005`, `ffiec_appendix_f`, `fatf_pml_2018`, `europol_money_muling`, `egmont_best_cases_2024` | |
| 6 | `fan_out_distribution` | [Fan-out distribution from one account](../typologies/fan-out-distribution.md) | [fan_out_distribution.yaml](../../detect/typologies/fan_out_distribution.yaml) | core | (f) | `fincen_fin_2006_g014`, `ffiec_appendix_f`, `fatf_pml_2018`, `fatf_cyber_fraud_2023`, `fincen_fin_2025_a003`, `europol_money_muling` | |
| 7 | `dormant_reactivation` | [Dormant account reactivation followed by high velocity](../typologies/dormant-reactivation.md) | [dormant_reactivation.yaml](../../detect/typologies/dormant_reactivation.yaml) | core | (j) | `ffiec_appendix_f`, `fatf_egmont_concealment_2018`, `fatf_cyber_fraud_2023`, `fatf_tcsp_2010`, `star_puppet_masters_2011` | |
| 8 | `shell_chain` | [Layered company ownership with nominee directors](../typologies/shell-chain.md) | [shell_chain.yaml](../../detect/typologies/shell_chain.yaml) | core | (g) | `fatf_egmont_concealment_2018`, `fatf_bo_legal_persons_2023`, `fatf_tcsp_2010`, `fatf_corporate_vehicles_2006`, `star_puppet_masters_2011`, `fincen_fin_2006_g014`, `europol_shadow_money_2021` | |
| 9 | `mass_registration_address` | [Mass registration addresses](../typologies/mass-registration-address.md) | [mass_registration_address.yaml](../../detect/typologies/mass_registration_address.yaml) | core | (h) | `fatf_egmont_concealment_2018`, `fatf_egmont_tbml_indicators_2021`, `fincen_fin_2006_g014`, `fatf_tcsp_2010`, `fatf_glossary`, `star_puppet_masters_2011`, `ffiec_appendix_f` | |
| 10 | `sanctions_exposure` | [Sanctions exposure through indirect ownership or control](../typologies/sanctions-exposure.md) | [sanctions_exposure.yaml](../../detect/typologies/sanctions_exposure.yaml) | core | (i) | `ofac_50_percent_2014`, `fatf_glossary`, `fatf_bo_legal_persons_2023`, `fatf_pf_sanctions_evasion_2025`, `fatf_egmont_concealment_2018`, `ffiec_appendix_f`, `icij_faq`, `opensanctions_glossary` | |
| 11 | `formation_agent_cluster` | [Companies clustered around one formation agent](../typologies/formation-agent-cluster.md) | [formation_agent_cluster.yaml](../../detect/typologies/formation_agent_cluster.yaml) | extended | (g) | `fatf_tcsp_2010`, `fatf_egmont_concealment_2018`, `fatf_corporate_vehicles_2006`, `star_puppet_masters_2011`, `fatf_glossary`, `fincen_fin_2006_g014`, `ffiec_appendix_f` | |
| 12 | `recycled_directors` | [Recycled and professional directors](../typologies/recycled-directors.md) | [recycled_directors.yaml](../../detect/typologies/recycled_directors.yaml) | extended | (h) | `fatf_egmont_concealment_2018`, `fincen_fin_2006_g014`, `europol_shadow_money_2021`, `fatf_glossary`, `fatf_tcsp_2010`, `ffiec_appendix_f`, `icij_faq` | |
| 13 | `pep_exposure` | [Exposure to politically exposed persons through ownership, control, family or associates](../typologies/pep-exposure.md) | [pep_exposure.yaml](../../detect/typologies/pep_exposure.yaml) | extended | (i) | `fatf_peps_2013`, `fatf_glossary`, `fatf_recommendations_2026`, `fatf_egmont_concealment_2018`, `ffiec_appendix_f`, `icij_faq`, `opensanctions_glossary` | |
| 14 | `cash_commingling` | [Cash-intensive business commingling](../typologies/cash-commingling.md) | [cash_commingling.yaml](../../detect/typologies/cash_commingling.yaml) | extended | (l) | `ffiec_cash_intensive`, `europol_efecta_2023`, `egmont_100_cases`, `fatf_pml_2018`, `fatf_cash_transport_2015`, `ffiec_appendix_f` | |
| 15 | `trade_based_ml` | [Trade-based money laundering (over- and under-invoicing)](../typologies/trade-based-ml.md) | [trade_based_ml.yaml](../../detect/typologies/trade_based_ml.yaml) | explainer_only | (k) | `fatf_egmont_tbml_2020`, `fatf_egmont_tbml_indicators_2021`, `fincen_fin_2014_a005`, `fincen_fin_2025_a003`, `fatf_pml_2018`, `ffiec_appendix_f` | |

Tiers: every `core` typology gets a detector and a labelled synthetic scenario (in Phase 3; `circular_flow` already in Phase 1), `extended` ones get detectors if Phase 3 has capacity, and `explainer_only` gets none ([PHASE-1.md](../build/PHASE-1.md) 7.2). The `core` typologies are needed first.

## 1. Read the draft

Read your explainer from top to bottom, then its definition file. Note what the draft claims: the definition, each red flag, each false positive, and the questions it lists under "Open questions" (claims the agent could not source, and decisions it left for the typology researcher). The explainer and the definition file should say the same thing; [_explainer-template.md](../typologies/_explainer-template.md) sets out the sections and their rules.

## 2. Read the sources

For each key in your row, open the entry in [bibliography.yaml](../sources/bibliography.yaml): the link, the `verified` date and the `note`. Read the parts of each source that the draft relies on, and enough around them to understand the context. Your research note entry points you to the right passages.

Read the `note` first. Some publishers, FATF and FFIEC among them, block automated clients, so the agent could not re-open their pages and took some quotes from the research note instead; one source (`fatf_corporate_vehicles_2006`) was verified only through FATF's index and may be quoted only after a manual download. Check the sentences that rely on these sources first: opening them in a browser is exactly what the agent could not do.

## 3. Check every sentence

Go through the explainer one sentence at a time. For each sentence that states a fact about money laundering, a source or the law, find the passage that supports it and write down where it is. Keep a table like this, which goes into your pull request description:

| # | Sentence (first words) | Key | Page, section or paragraph | Verdict |
|---|---|---|---|---|
| 1 | {first words of the sentence} | `{key}` | {page, section or paragraph} | {correct, fixed, added, removed or moved to Open questions} |

Ask of every sentence:

- Does the cited source say this, at the place you found? A key that points at the wrong source is an error even when the sentence is true.
- Is a quotation word for word, in quotation marks, with its key? Otherwise paraphrase and cite ([how to cite](../sources/README.md)).
- Does the paraphrase keep the source's meaning, including its hedges ("may", "often", "in some cases")?
- Is the statement about a pattern, never about a named person, company or account?

Check the definition file the same way: `summary`, `graph_pattern`, `false_positives` and `citations` must match the explainer.

## 4. Fix what is wrong, add what is missing

- **Wrong:** correct the sentence, change the key, or remove the sentence. If no bibliography source supports a statement, move it to "Open questions" rather than leaving it uncited.
- **Missing:** if a cited source says something important about the pattern that the draft leaves out (a red flag, a false positive, a limit), add it with its key. If the source you need is not in the bibliography yet, add an entry as [How to add a source](../sources/README.md#how-to-add-a-source) describes, and say so in your pull request.
- **Open questions:** answer the ones your sources settle, with citations, and remove them from the list. Leave decisions about parameters and modelling for the typology researcher.
- **Citations in both places:** every key the explainer cites appears in its "Sources" section and in the definition file's `citations`.
- Where it helps a reader, put the page or section after the key, as the glossary does: `[fatf_egmont_concealment_2018] (executive summary, p. 5)`.
- **What you edit in the definition file:** `summary`, `graph_pattern`, `false_positives` and `citations`, so that they match the explainer.
- **Leave alone:** `slug`, `name`, `version`, `status`, `approved_by`, `owner`, `tier`, `synthetic_support`, `generator_scenario`, `detector`, `parameters`, `metrics` and `wording`. The tier and the synthetic support set what Phase 3 builds, and parameters and wording templates are the typology researcher's decision. Propose any change to them in your pull request description, with the reason.

## 5. Run the checks

From the repository root:

```bash
make check      # includes the typology catalog tests
make hygiene    # citations, the wording lint and the other pull request checks
```

`scripts/check_citations.py` (part of `make hygiene`) fails when a cited key is not in the bibliography. The wording lint ([forbidden patterns](../wording.md#forbidden-patterns)) covers the definition file's `false_positives` too: the catalog tests in `make check` fail when a false positive uses a forbidden term such as "fraud", "suspicious", "mule" or "shell company", so describe the ordinary activity in neutral words.

## 6. Open a pull request

```bash
git fetch origin
git switch -c assignment-2/<your-handle> origin/main
git add docs/typologies/<explainer>.md detect/typologies/<slug>.yaml
git commit -m "docs(detect): check the <slug> explainer against its sources"
git push -u origin assignment-2/<your-handle>
gh pr create --web
```

- **Title:** Conventional Commits, which CI checks, for example `docs(detect): check the circular_flow explainer against its sources (@your-handle)`.
- **Body:** fill in the [pull request template](../../.github/pull_request_template.md). Summary: what you changed and why. Milestone: Assignment 2. Human owner: you. Acceptance evidence: your sentence table from step 3 and the last lines of `make check` and `make hygiene`. Contract impact: none. Data and licence impact: no data files added. AI involvement: say honestly whether and how you used AI. List the changes you propose to fields you left alone under "Not addressed".
- **Labels:** `learning` and `typology`. If you cannot add labels, your reviewer adds them.
- **Commit only** your explainer, its definition file and, if you added a source, `docs/sources/bibliography.yaml`.
- If the project lead opened an issue "Assignment 2: <slug>" for you, write `Closes #<number>` in the body.

[CODEOWNERS](../../.github/CODEOWNERS) asks the owners of `docs/typologies/` and `detect/typologies/`, the typology researchers, to review.

## 7. Be ready to explain every change

The typology researcher reviewing your pull request may ask:

- Where in the source is this? Show the page and read the passage.
- Why did you change or remove this sentence? What did the draft get wrong?
- Is this quotation word for word?
- How often does this false positive happen in ordinary business, and what tells it apart from the pattern?
- What can NeonRadar's graph not show about this typology?

"The AI wrote it" is not an answer, and neither is "the agent's draft said so". An AI tool can help you find a passage or phrase a sentence, but checking means reading the passage yourself. If you cannot settle a point, say so in the pull request and write down what confused you in your learning log.

## Review checklist for typology researchers

Use it on every Assignment 2 pull request, and again before approving.

- [ ] **Every claim traced.** Each factual sentence has a key, and the sentence table names the page, section or paragraph. Check every quotation against the source, and spot-check other sentences.
- [ ] **Citations in both files.** Every key cited in the explainer exists in the bibliography, appears in its "Sources" section and is in the definition file's `citations`.
- [ ] **Glossary terms** ([glossary.md](../glossary.md)). "Beneficial owner" means a natural person only [fatf_glossary]; a company that owns a company is a legal or intermediate owner. STR in FATF and non-US contexts, SAR for US material. "Nominee", with "strawman" and "proxy" as synonyms.
- [ ] **The 25 percent figure** is an illustrative FATF example that became law in the EU and elsewhere, not a FATF requirement [openownership_thresholds] [eba_qa_2022_6622]. The page never presents it as a FATF threshold.
- [ ] **Patterns, not accusations** ([documentation rules](../wording.md#documentation-rules), [vocabulary](../wording.md#vocabulary-for-entity-facing-text)). The explainer may discuss money laundering as a subject, but it never says that a person, company or account did anything, and it never calls a real, named company a shell, front or mule account. Red flags are presented as reasons to look closer, not evidence [ffiec_appendix_f]. The `wording` templates and every `false_positives` entry pass the wording lint.
- [ ] **False positives realistic.** Each look-alike is ordinary activity that produces the same shape, the page says what tells it apart, and the definition file's `false_positives` agree with the explainer. The Phase 3 generator must be able to produce them.
- [ ] **Real cases.** Only institutions that admitted facts and individuals who were convicted (with the court level) are named as wrongdoers; victims, publishers, courts and authorities only in those roles; everyone else by role; what was adjudicated is separated from what is alleged, and the date the status was checked is given.
- [ ] **Standing disclaimer intact.** The paragraph under the banner that links the [standing disclaimer](../wording.md#disclaimers) is unchanged, and no disclaimer text has been edited.
- [ ] **Generic examples.** Diagrams and examples use labels such as "Account A", never real names or addresses.
- [ ] **Explainer and definition agree**, and the definition file still says `status: draft` and `approved_by: null`.
- [ ] **CI passes**, including the citation check, the wording lint and the typology index check.

## Who approves a typology

A typology's `status` changes only through a typology researcher's approval ([roles.md](roles.md)):

1. Your pull request leaves the definition file at `status: draft` with `approved_by: null`. The assignee never sets either field, and neither does any agent ([OD-5](../build/operator-decisions.md); [CLAUDE.md](../../CLAUDE.md) rule 4).
2. A typology researcher reviews your pull request with the checklist above and asks for changes until it passes.
3. Once it is merged and the researcher is satisfied, the researcher opens their own pull request that sets `status: approved` and `approved_by` to their own handle, updates the explainer's "Draft" banner and regenerates the catalog index with `uv run neonradar docs typology-index` (CI checks it with `--check`).

The catalog refuses `status: approved` without `approved_by` ([C4 alert contract](../../contracts/C4-alert.md)). While one person holds every role ([OD-6](../build/operator-decisions.md)), that person is the only typology researcher.

## Afterwards

- Write a learning log entry about your typology ([docs/learning/README.md](../learning/README.md)): what surprised you in the sources, and what the draft got wrong. You write it yourself; no agent writes it for you.
- Your typology is a good topic for a [teach-back session](../learning/teach-back.md).
- For background, read the [reading list](../learning/reading-list.md) and the [case notes](../learning/cases/README.md). The case notes show which typologies three real cases illustrate, and how to write about a real case: roles instead of names, and what was adjudicated kept apart from what is alleged.

## Sources

- [eba_qa_2022_6622] European Banking Authority, *Single Rulebook Q&A 2022_6622*, 2022. <https://www.eba.europa.eu/single-rule-book-qa/qna/view/publicId/2022_6622>
- [fatf_glossary] FATF, *FATF Glossary (web version of the General Glossary)*, living document. <https://www.fatf-gafi.org/glossary/>
- [ffiec_appendix_f] FFIEC, *BSA/AML Examination Manual, Appendix F: Money Laundering and Terrorist Financing Red Flags*, living document. <https://bsaaml.ffiec.gov/manual/Appendices/07>
- [openownership_thresholds] Open Ownership, *Beneficial ownership in law: Definitions and thresholds (thresholds)*, living document. <https://www.openownership.org/en/publications/beneficial-ownership-in-law-definitions-and-thresholds/thresholds/>
