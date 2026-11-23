# Demo day

Every Friday, 30 minutes, the squads show what they got working that week to the whole team. People remember demos; they do not remember merged pull requests ([project plan](../plan/neonradar-project-plan.md), "Friday demo, every week, run by the squads"). Together with the Thursday [teach-back](../learning/teach-back.md), it makes the team's weekly rhythm:

| Day | Session | Length | Organised by | Who shows |
|---|---|---|---|---|
| Thursday | [Teach-back](../learning/teach-back.md): something you learned | 30 minutes | Community manager (fills the rota) | Two or three people |
| Friday | Demo: something that works | 30 minutes | Release manager (runs the demo) | Each squad that has something new |

The release manager rotates weekly and also cuts the demo build ([roles.md](roles.md)). The project lead confirms or moves each teach-back's date ([OD-1](../build/operator-decisions.md)); this page suggests the same for demos.

## The 30 minutes

| Minutes | What |
|---|---|
| 0 to 3 | The release manager: is the integration branch (`dev` at present; `CONTRIBUTING.md` says `main`) green, what merged this week, what is next week's goal |
| 3 to 24 | Each squad with something new shares these 21 minutes equally: about 5 minutes for four squads, about 3 when all six show. Show the real thing running, not slides. Say what it does not do yet |
| 24 to 30 | Questions, and one line each on what is blocked. A blocker that needs a person in a role to decide becomes an issue labelled `needs-human-decision` |

A squad with nothing new that week says so in one sentence; that is useful too.

## Before the demo (release manager)

- [ ] Ask each squad, ideally by Thursday evening, whether it will show something, and in what order.
- [ ] Cut the demo build: a clean clone of the integration branch, `make setup`, `make demo-mini` ([quickstart](../quickstart.md)). If it does not start, that is the first thing to show, and the first thing to fix.
- [ ] Run the [screenshot and video policy](../screenshot-policy.md) checklist on the screen that will be shared: the synthetic demo notice visible, only `syn-` ids, no `.env` or password on screen, no personal windows or notifications.

## Rules for what is shown

- **Synthetic data only.** Never show a real person or company next to a pattern ([PHASE-1.md](../build/PHASE-1.md) G1). A loader that has run on real data is shown with counts only ([PHASE-2.md](../build/PHASE-2.md) G9).
- **Patterns, never accusations,** in the voice-over too: say "matches the graph pattern of", not "suspicious" ([wording.md](../wording.md)).
- **No secrets** on screen, in the chat or in the recording.

## Recording

As for teach-backs, ask for consent before recording: from everyone presenting, and from anyone who speaks in the questions. Recordings are not stored in the repository, and the project lead decides where they live ([teach-back.md](../learning/teach-back.md), "Recording"). Anything published follows the [screenshot and video policy](../screenshot-policy.md).

## Demo log

The release manager adds one row after each demo. Dates and names are filled in by the people who ran it.

| Date | Release manager | What was shown, by squad | Blockers raised | Recording |
|---|---|---|---|---|
| | | | | |
