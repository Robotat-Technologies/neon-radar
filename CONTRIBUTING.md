# Contributing to NeonRadar

> Draft. This guide grows with the project during Phase 1; the build spec in [docs/build/](docs/build/) is the reference until then.

Thank you for helping. Documentation, typology definitions, synthetic fixtures and licence notes are contributions in the same way as code, and they get the same review.

## How a change happens

1. **Open an issue first.** Use one of the issue forms (bug, feature, typology, data source, contract change) so the work is agreed before anyone writes it. Security issues never go in a public issue; see [SECURITY.md](SECURITY.md).
2. **Create a branch** from an up-to-date `main`.
3. **Open a pull request** and fill in every section of the [pull request template](.github/pull_request_template.md): summary, milestone, human owner, acceptance evidence, contract impact, data and licence impact, AI involvement, deviations from spec and anything not addressed.
4. **Get a review from a member of another squad.** Code owners in [.github/CODEOWNERS](.github/CODEOWNERS) are asked automatically for the paths they own.

## Rules for every pull request

- **You must be able to explain every line.** The author must be able to explain every line, and "the AI wrote it" is not an answer.
- **Agent pull requests are labelled `agent` and name a human owner**, one person who is accountable for the change.
- **Commits follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/):** `type(scope): summary`. Types: `feat`, `fix`, `docs`, `test`, `refactor`, `build`, `ci`, `chore`. Scopes: `repo`, `build`, `ci`, `contracts`, `ingest`, `graph`, `detect`, `copilot`, `api`, `cli`, `ui`, `docs`, `data`, `agent`.
- **Keep pull requests small:** at most 400 changed lines of code, tests and configuration. Markdown, typology YAML files, the bibliography, lock files, generated files, fixtures, examples and research notes are not counted; [.github/pr-size-exclude.txt](.github/pr-size-exclude.txt) lists them. Documentation is reviewed by reading, not by line count. A milestone that the build spec marks `Size: exception` carries the `size-exception` label; any other change that would exceed the limit is split into several pull requests.
- **Bring a branch up to date by merging `main` into it**, never by rebasing a pushed branch or force-pushing.
- **Follow the guardrails** in [docs/build/PHASE-1.md](docs/build/PHASE-1.md) section 2.1. In short: no real person or company is ever labelled suspicious; the repository holds code and synthetic fixtures only; nothing phones home; AML facts carry citations; text about entities describes patterns, never accusations; secrets stay out; licences decide what a loader may do.

## Who merges

During the initial build, the operator has authorised the orchestrating agent session to merge a pull request after its acceptance checks pass, an independent review finds nothing left that affects correctness, the stated requirements or the guardrails, and CI passes (once CI is in place). Humans review merged work afterwards. Humans own, and never delegate to an agent, the decisions that need human judgement: freezing a contract or tagging a contract version, approving a typology definition, accepting an architecture decision record and confirming a licence decision; and everyone writes their own learning logs, self-assessments, teach-backs, exit posts and assignment submissions. See [docs/build/operator-decisions.md](docs/build/operator-decisions.md) (OD-2, OD-5 and OD-8).

## Where things are

- [docs/build/](docs/build/): the build spec, project facts, operator decisions and the progress log.
- [docs/](docs/README.md): an index of all project documentation.
- [DATA_SOURCES.md](DATA_SOURCES.md): every data source and its licence.
- [CONTRIBUTORS.md](CONTRIBUTORS.md): who owned what.

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).
