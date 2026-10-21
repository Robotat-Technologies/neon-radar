# Learning track

When AI drafts most of the code, people do not learn by watching it happen. Learning has to be built into the project on purpose, and it is the thing everyone keeps after 20 November ([project plan](../plan/neonradar-project-plan.md), "Learning track"). Three habits do most of the work, because each one makes you produce an explanation instead of accepting one:

1. **Defending your pull request in review.** You must be able to explain every line ([CONTRIBUTING.md](../../CONTRIBUTING.md)).
2. **Owning decision records.** The agent drafts architecture decision records as `proposed`; the people who decide edit them until they say what they think, and accept them ([docs/decisions/](../decisions/README.md)).
3. **Teaching it back.** Thirty minutes on Thursdays, two or three people at a time ([teach-back.md](teach-back.md)).

This folder holds the rest of the track: your learning log, the skills self-assessment and, in the final week, your exit post.

| File | What it is | Who writes it |
|---|---|---|
| [_template.md](_template.md) | The learning log template | Copy it to start your log |
| `<your-handle>.md` | Your learning log | You, and only you |
| [skills-self-assessment.md](skills-self-assessment.md) | The eight skills and the 1 to 5 scale | You score yourself, in your own log |
| [teach-back.md](teach-back.md) | Sessions, rota and recordings | The community manager fills the rota; presenters prepare their talk |

The reading list and the case notes arrive here with milestone M1.10c.

## Your learning log

**Why it exists.** Each week you write down what you read, what you built, what you got wrong and what still confuses you. Over six weeks that becomes a record of what you actually learned, for you and for the team, and evidence of what the internship taught.

**Three to five lines a week.** Short and honest beats long and polished. Nobody grades it.

**Honest confusion is the most valuable content.** "I still do not see why the loader needs two passes" is a good entry. Do not tidy confusion away; reviewers welcome it, and it often shows where the documentation is missing.

**Start it in your first week:**

```bash
cp docs/learning/_template.md docs/learning/<your-handle>.md   # your GitHub handle, without the @
```

Fill in the header, score yourself in the skills table (the "Start" column), and write your first entry. [Assignment 1](../team/assignment-1.md) is a good first entry.

**Each week** add one entry: a heading `### Week of YYYY-MM-DD` (the Monday of that week) with your lines under it, newest at the bottom. Commit it with your other work, or in a small pull request of its own labelled `learning`, for example `docs(docs): add week 2 to my learning log`.

**It is yours.** Only you write in your log. Reviewers comment on the pull request rather than editing your file. No agent writes or edits learning logs, self-assessments, teach-backs or exit posts for anyone (build spec [PHASE-1.md](../build/PHASE-1.md) 1.9, operator decision [OD-5](../build/operator-decisions.md)); you may use AI to look things up, but the words are yours.

The Gate 1 check GC-12 looks for `docs/learning/<handle>.md` with at least one entry for everyone listed in `people.interns` in [project.yaml](../build/project.yaml).

## Skills self-assessment

You score yourself from 1 to 5 on eight skills, once in your first week and once in the final week. The skills and the scale are in [skills-self-assessment.md](skills-self-assessment.md); the table you fill in is in your log.

## Exit post

In the final week, write a short post: what I built, what I learned, what I would do differently. Put it next to your log as `docs/learning/<your-handle>-exit.md`. The best lines may go into the launch post, with your agreement, and you keep something concrete to show for six weeks of work.
