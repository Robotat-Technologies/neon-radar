# Issue triage rota

Each week one person reads every new issue, labels it, sizes it and routes it to the people who own it, so that nothing sits unanswered. This page is the routine and the rota. The community manager keeps the rota filled, because [roles.md](roles.md) gives that role the issue templates and good first issues.

## The rota

One triager per week, Monday to Sunday. The community manager fills a row before the week starts; anyone may swap a week with someone else by editing the row.

| Week of | Triager | Handed over |
|---|---|---|
| | to be assigned | |

When the week ends, the triager writes in "Handed over" anything still open (for example "#164 waits for the UI squad"), so the next triager starts from it.

## Each issue, once

Work through the new issues oldest first. For each one:

1. **Is it in the right place?**
   - A security report does not belong in a public issue. Do not discuss the details in the issue; ask a maintainer to hide it, and point the author to [SECURITY.md](../../SECURITY.md). Until `SECURITY.md` names a contact, route the report to the project lead.
   - An issue must never hold a real name, birth date, address or identifier ([PHASE-2.md](../build/PHASE-2.md) G9), and must never put a real person or company next to a pattern ([PHASE-1.md](../build/PHASE-1.md) G1). Ask the author to replace it with a synthetic example, and ask a maintainer to hide or edit the content.
   - A duplicate gets the `duplicate` label and a link to the original, then is closed.
2. **Label it.** The issue form already adds the type: `bug`, `enhancement`, `typology`, `data-source` or `contract-change`. Add:
   - the squad label from the table below;
   - `good first issue` if a newcomer could do it in a few hours with the docs as they are, and `help wanted` if the owning squad asks for it;
   - `needs-human-decision` if only a person in a role can unblock it (a contract freeze, a typology approval, a decision record, a licence), and `blocked` if it waits on something else. Say what it waits on in a comment.
3. **Size it**, in a comment: **S** (a few hours) or **M** (about a week). Anything bigger is split into issues that each fit one pull request of at most 400 changed lines ([CONTRIBUTING.md](../../CONTRIBUTING.md)).
4. **Route it.** Mention the owning squad's mentor (and its GitHub team, once the `neonradar` organisation and its teams exist; [roles.md](roles.md)), and the role in the table below if the issue needs one. Assign a person only if they agreed to take it.
5. **Answer it.** Every new issue gets a human reply in the week it arrives, even if the reply is only "labelled and routed to the UI squad".

## Who owns what

Squads follow the paths in [CODEOWNERS](../../.github/CODEOWNERS); roles follow [roles.md](roles.md).

| The issue is about | Squad label | Route it to |
|---|---|---|
| `ingest/`, `data/fixtures/`, a loader | `squad:ingest` | The ingest squad; a new or changed source also to the data steward (`data-source`) |
| `graph/`, `keys/`, `resolve/` (entity resolution) | `squad:graph` | The graph squad |
| `detect/`, `eval/`, a typology or detector | `squad:detect` | The detect squad; a typology definition also to the typology researchers, the only people who approve one |
| `copilot/`, `api/` | `squad:copilot` | The copilot squad |
| `ui/` | `squad:ui` | The UI squad |
| `docs/`, `cli/`, root files, `.github/`, the `Makefile` | `squad:docs` | The docs squad |
| `contracts/`, `graph/schema/` | the squad whose code the change serves | The tech lead. The contract-change form starts the process; no pull request before the tech lead approves |
| `DATA_SOURCES.md`, a licence | none (the data source form adds `data-source`) | The data steward |
| `docs/build/`, `.claude/` | none | The project lead |

## Each week

Run these at the start and end of your week, from the repository folder. They read GitHub; they change nothing.

```bash
gh issue list --state open --limit 200 --search "no:label"                   # never labelled
gh issue list --state open --limit 200 --search "comments:0"                 # never answered
gh issue list --state open --limit 200 --search "-label:squad:ingest -label:squad:graph -label:squad:detect -label:squad:copilot -label:squad:ui -label:squad:docs"   # no squad yet
gh issue list --state open --limit 200 --label blocked                       # still blocked: is the reason still true?
gh issue list --state open --limit 200 --label needs-human-decision          # waiting on a person in a role
```

Close an issue only when it is done, a duplicate, or out of scope with a reason in the comment. If you are not sure, leave it open and ask in "Handed over".
