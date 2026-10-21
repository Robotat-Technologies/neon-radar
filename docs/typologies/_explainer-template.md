# Typology explainer template

Copy this file to `docs/typologies/<slug with hyphens>.md` (for example `circular-flow.md` for the slug `circular_flow`), replace every part in curly braces, and delete this introduction and the guidance under each heading. Use it with the `/typology-draft` skill. The rules for every explainer:

- Every factual statement about money laundering cites a key from [the bibliography](../sources/bibliography.yaml), in square brackets right after the statement ([how to cite](../sources/README.md)). Quote only in quotation marks, with the key; otherwise paraphrase and cite.
- If a statement has no source in the bibliography, leave it out and list it under "Open questions". Never invent a definition, threshold or law.
- Describe patterns, never accusations: an explainer may discuss money laundering as a subject, but it never says that a person, company or account did anything ([docs/wording.md](../wording.md)). Use the terms in [the glossary](../glossary.md).
- Real cases name as wrongdoers only institutions that admitted facts and individuals who were convicted, with the court level. Victims, publishers, courts and authorities may be named in those roles; everyone else is described by role. Separate what was adjudicated from what is alleged, and give the date the status was checked ([docs/wording.md](../wording.md), documentation rule 3).
- Write for a new intern: short sentences, one idea each, and explain each graph term the first time it appears.
- The definition file (`detect/typologies/<slug>.yaml`) and this page say the same thing. Only a typology researcher sets the definition to `approved`.

---

# {Typology name}

> **Draft.** Slug `{slug}`, version {version}, tier `{tier}`, synthetic support `{synthetic_support}`. Definition file: [`detect/typologies/{slug}.yaml`](../../detect/typologies/{slug}.yaml). A typology researcher checks this page against its sources before the definition is approved.

A structure that matches this pattern is not evidence of money laundering or of any other wrongdoing. There are ordinary reasons for almost every pattern described here; the [standing disclaimer](../wording.md#disclaimers) applies to everything NeonRadar shows.

## What it is

{Two to four short paragraphs in plain language: what the typology is and where the sources describe it, each statement with its citation. Name the stage it belongs to (placement, layering or integration) only when a source does.}

## How it looks in the graph

{The graph pattern in C2 terms (`contracts/C2-graph-schema.md`): which nodes (`:Account`, `:LegalEntity`, `:Address`, ...), which relationships (`PAID`, `HOLDS_ACCOUNT`, `OWNS`, ...) and which properties (`amount`, `ts`, `channel`, ...). Add a small Mermaid diagram with generic labels such as "Account A", never real names. Say what the graph cannot show (for example data C2 does not store).}

## Red flags the sources list

{A bullet list of red flags from the sources, quoted or paraphrased, each with its citation. End with: a red flag is a reason to look closer, not evidence.}

## Typical false positives

{The benign look-alikes from PHASE-1.md 7.2 and the research note: ordinary activity with the same shape. Say what tells them apart. The Phase 3 generator produces these look-alikes so that precision is measured honestly.}

## Can synthetic data show it?

{The synthetic support level from PHASE-1.md 7.2 (high, medium, low or none) and why: which parts of the pattern the generator controls, which look-alikes it must also produce, and what synthetic data cannot show. Planted scenarios run only among synthetic entities (guardrail G1).}

## Starting parameters

{The parameters a detector would need, with the starting values from PHASE-1.md 7.2 or the definition file. Say that they are starting points for the typology researcher, not facts from the sources. Write "None yet" when there are none.}

## Open questions

{Statements left out because no bibliography source supports them yet, and decisions for the typology researcher. Write "None" when there are none.}

## Sources

{Each key cited on this page, in alphabetical order, with publisher, title in italics, year (or "living document") and link, in the form used at the end of the glossary.}
