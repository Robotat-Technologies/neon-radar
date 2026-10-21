# Sources and how to cite them

Every factual statement about money laundering, its typologies, its law or its cases in NeonRadar's documentation cites a source from [bibliography.yaml](bibliography.yaml) (guardrail G4 in [docs/build/PHASE-1.md](../build/PHASE-1.md) section 2.1). This page explains how to cite, how to add a source and how the check works.

## How to cite

**In Markdown**, put the key in square brackets right after the statement it supports, one key per bracket:

```markdown
A money mule receives money from a third party and transfers it on [europol_money_muling].
```

- Quote a source only in quotation marks, with its key. Otherwise paraphrase and cite.
- A document that cites ends with a `## Sources` section that lists each key it used, with title, publisher, year and link (see the end of [docs/glossary.md](../glossary.md) for an example).
- To show a key as text without citing it, put it in inline code, as this page does.

**In typology files** (`detect/typologies/<slug>.yaml`), keys go in the `citations` list:

```yaml
citations: [fatf_egmont_concealment_2018, ffiec_appendix_f]
```

**Wording and terminology.** Use the terms in [docs/glossary.md](../glossary.md) and follow the wording rules in [docs/wording.md](../wording.md). A red flag or indicator is a reason to look closer, not evidence [ffiec_appendix_f].

## How to add a source

1. Open the source and check that it says what you will cite it for.
2. Add an entry to `bibliography.yaml`:

   ```yaml
   - key: fatf_pml_2018
     title: Professional Money Laundering
     publisher: FATF
     year: 2018                 # null for a living document, with a note that says so
     url: https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Professional-Money-Laundering.pdf.coredownload.pdf
     extra_urls: []             # mirrors, annexes, an index entry
     verified: 2026-10-16       # the date you opened the url
     note: Professional launderers, mule networks, proxy networks of shell company accounts.
   ```

3. Choose the key in lowercase snake case with at least one underscore, publisher first; a dated source ends with its year (`fincen_fin_2006_g014`, `europol_efecta_2023`).
4. If you could verify the source only indirectly, could not open it, or a title still needs confirming, say so in `note`. If a URL no longer resolves, keep the entry, record what happened in `note` and ask the typology researchers.

Some publishers (fatf-gafi.org, bsaaml.ffiec.gov, justice.gov, eba.europa.eu, register.openownership.org, eur-lex.europa.eu) answer automated clients with a bot challenge. Entries from those sites keep the date a person or the research note last opened them, and their note says to re-open them in a browser.

## The check

`scripts/check_citations.py` checks that every key cited in the documentation exists in the bibliography:

```bash
uv run python scripts/check_citations.py docs/ detect/typologies/ README.md
```

- In Markdown, outside fenced code blocks and inline code, every match of `\[([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\](?![(\[])` must be a key. The pattern skips links, task boxes and ordinary bracketed words.
- In `detect/typologies/*.yaml`, every entry of `citations` must be a key.
- It skips `docs/research/` and `docs/plan/`, which keep source material as delivered.
- It also fails when the bibliography has a duplicate key, a key that cannot be cited, or an entry without `key`, `title`, `publisher`, `year`, `url` or `verified`.

`make hygiene` and the `python` job in CI run it on every pull request.

## Sources

- [ffiec_appendix_f] FFIEC, *BSA/AML Examination Manual, Appendix F: Money Laundering and Terrorist Financing Red Flags*, living document. <https://bsaaml.ffiec.gov/manual/Appendices/07>
