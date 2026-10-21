# Teach-back sessions

Thirty minutes on a Thursday, two or three people present something they learned to the rest of the team. Across the project everyone presents at least once. Sessions are recorded, and the good ones become documentation ([project plan](../plan/neonradar-project-plan.md), "Learning track"). The plan asks for six recorded sessions ("Definition of done": "Six teach-back sessions held, with everyone having presented at least once").

## Sessions and rota

The dates below are the plan. Dates are informational ([OD-1](../build/operator-decisions.md)): the project lead confirms each session or moves it. The community manager (`people.community_manager` in [project.yaml](../build/project.yaml)) fills in the presenters, two or three per session, so that everyone on the team presents once before the end. Presenters add their own topic.

| # | Planned date | Presenter 1 | Presenter 2 | Presenter 3 (optional) | Topics | Recording |
|---|---|---|---|---|---|---|
| 1 | Thursday 22 October 2026 | | | | | |
| 2 | Thursday 29 October 2026 | | | | | |
| 3 | Thursday 5 November 2026 | | | | | |
| 4 | Thursday 12 November 2026 | | | | | |
| 5 | Thursday 19 November 2026 | | | | | |
| 6 | Scheduled by the project lead, or Thursday 15 October 2026 if that session took place | | | | | |

## Presenting

- About ten minutes each, questions included. No slides needed: show the real thing, such as a query, a pull request, a test or a mistake.
- Teach one thing you learned in the project and how you learned it: a Cypher pattern, why the loader works the way it does, how a typology is defined in its source, a review comment that changed your mind.
- What confused you is a good topic. Someone else is confused by it too.
- Show synthetic data only. Never show a real person or company next to a pattern (guardrail G1 in [PHASE-1.md](../build/PHASE-1.md) 2.1).
- You prepare and give your own talk. Agents do not write teach-backs for anyone ([OD-5](../build/operator-decisions.md)).

## Recording

- Ask everyone presenting for consent at the start, then record.
- Recordings are not stored in the repository: it holds code and synthetic fixtures only (guardrail G2). The project lead decides where they live; put the link in the "Recording" column.

## Good ones become documentation

After each session the community manager and the presenters pick the talks worth keeping. The presenter turns their talk into a page under `docs/`, in their own words, through a normal pull request labelled `learning`, and links the recording.
