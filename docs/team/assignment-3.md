# Assignment 3: label pairs for the precision figure

| | |
|---|---|
| Who | Every intern (`people.interns` in [project.yaml](../build/project.yaml)). Every intern is also a labeller (`people.er_labellers`), and mentors who label join you |
| Due | Tuesday 3 November 2026; the teach-back is on Thursday 5 November 2026. Dates are a plan, not a deadline the build enforces ([OD-1](../build/operator-decisions.md)); the project lead confirms them or moves them |
| You hand in | At least 20 labels from one session with `neonradar er label` (they stay on the labelling machine); five hard cases in your own learning log, described by their features only; one case presented at the teach-back |
| AI help | Allowed for understanding the method. Never for labelling (guardrail G10): never paste anything from a card into an AI tool, and never label where an AI assistant can read the terminal or the screen |

## Why

NeonRadar publishes one number about its entity resolution: how many of the merges it made on a slice of the UK register are right ([PHASE-2.md](../build/PHASE-2.md) 7.3). No program can measure that, because the right answer exists only in the world, not in the data; people have to judge sampled pairs. Your labels are that measurement, and the agent that builds NeonRadar never labels, because a figure measured by the system's own builder would mean nothing (G10).

On the way you learn how record linkage works, why names are weak evidence, and how a published figure can be honest about what it does not know. That is the Sprint 1 learning goal of the [project plan](../plan/neonradar-project-plan.md) ("Learning track"): Splink and the Fellegi-Sunter model.

## Before you can start

The labelling session needs things that only humans set up. The graph mentor tells you when they are in place:

- **You are a labeller.** Your GitHub handle is in `people.interns` and in `people.er_labellers`. Today both lists still wait for the team to join ([OD-6](../build/operator-decisions.md), [OD-22](../build/operator-decisions.md)).
- **Real data may be loaded.** The data steward has filed the data protection documents and allowed the `uk-sample` profile (`access.data_protection_filed` and `access.real_data_profiles`); until then no real profile runs (OD-22).
- **You have an approved machine** and a booked two-hour session on it ([real-data-machines.md](../data/real-data-machines.md); [PHASE-2.md](../build/PHASE-2.md) 1.1).
- **The sample exists.** The operator has made the evaluation run and drawn the sample with `neonradar er sample`, which splits the pairs across every handle in `people.er_labellers` (PHASE-2.md M2.15, steps 1 and 2). The tools come with milestone M2.10c.

You can do steps 1 and 2 below before any of this is ready.

## 1. Read

1. Splink's guide to [the Fellegi-Sunter model](https://moj-analytical-services.github.io/splink/topic_guides/theory/fellegi_sunter.html) [splink_docs]: m and u probabilities, match weights and match probability. The original paper is Fellegi and Sunter (1969) [fellegi_sunter_1969]; reading it is optional.
2. NeonRadar's [entity resolution overview](../er/README.md): how records become entities here, why the merge policy keeps listed and leaked records apart, and how the figure is measured.
3. The [labelling guide](../er/labelling-guide.md), all of it, including the privacy rules. Work through the ten worked examples before you read their answers: if you disagree with an answer, ask the graph mentor before your session, not during it.

Write in your [learning log](../learning/README.md#your-learning-log) what you read and what still confuses you.

## 2. Practise on synthetic data (optional)

Once M2.10c has merged, you can try the tool on the synthetic `demo` profile on any machine; these labels are practice and never count:

```bash
uv run neonradar er run --profile demo --no-decisions
RUN="$(cat data/cache/synthetic/resolution/demo/LATEST)"
uv run neonradar er sample --profile demo --run "$RUN" --seed 7 --labellers @your-handle,@practice-partner
uv run neonradar er label --profile demo --run "$RUN" --labeller @your-handle
```

`er sample` needs at least two different handles, because each overlap pair goes to two people ([PHASE-2.md](../build/PHASE-2.md) 7.3 rule 4): practise with another intern's handle, or keep `@practice-partner` and leave its pairs unlabelled. The `demo` records are invented, but practise the habits of a real session anyway: no screenshots, and notes that say only how the fields compare.

## 3. Label at least 20 pairs in one session

On the approved machine, at a terminal, in your booked session:

```bash
uv run neonradar er label --profile uk-sample --run <run id> --labeller @your-handle
```

The graph mentor gives you the run id. For each pair, read both cards completely, decide as the [labelling guide](../er/labelling-guide.md#how-to-judge-from-partial-information) says, and answer `s` (same), `d` (different) or `u` (unsure), with a note that says only how the fields compare when the decision was close or you answered `unsure`. Aim for at least 20 pairs; label more if your session allows. Some of your pairs are also labelled by another person, to measure agreement; you will not know which.

The [privacy rules](../er/labelling-guide.md#privacy-rules-for-labelling-sessions) hold for the whole session: approved machine, no screenshots, no names or other card values outside the session, no web searches about the people on the cards and no opening their source links, no AI tools (and a plain terminal that no AI assistant can read), labels never copied anywhere.

## 4. Write five hard cases in your learning log

After the session, add an entry to your own learning log with the five pairs you found hardest. Describe each **by its features only**: say how the fields compare (agree, differ, missing, one year apart), as in "same surname, birth years one apart, different nationality" or "same postcode district, different companies", not who it was. Never write a value from a card, even one that seems harmless: no name, date, nationality, town, postcode, company name or sector, identifier or record id. For each case write:

- the features that agreed, differed or were missing;
- your answer and why;
- what would have decided it, if anything.

Commit the entry in a pull request of your own, labelled `learning`, as for any log entry ([docs/learning/README.md](../learning/README.md)). You write it yourself; no agent writes or edits learning logs ([OD-5](../build/operator-decisions.md)).

## 5. Present one case at the teach-back

At the [teach-back](../learning/teach-back.md) on Thursday 5 November 2026, present one of your five cases in a few minutes: the features, your answer, and what you learned from it. Show no real data: no card, no screenshot, no name or other value from a card. If you want to show cards, find a pair with the same shape in the synthetic benchmark (`data/fixtures/er-bench/`) and show that instead, as the labelling guide's worked examples do.

## How it is checked

- **Labels.** The graph mentor reports how many pairs each handle labelled, from the label files on the labelling machines; at least 20 per intern is Gate 2 check G2-13, which a human confirms (the agent never reads label files) ([PHASE-2.md](../build/PHASE-2.md) section 8).
- **Hard cases.** Your learning log pull request: the reviewer checks that every case says only how the fields compare and holds no value from a card (no name, date, nationality, town, postcode, company name or sector, identifier or record id).
- **Teach-back.** One case each, on Thursday 5 November.

Nobody grades your labels against an answer key: there is none. An honest `unsure` is better than a confident guess.

## Sources

- [fellegi_sunter_1969] Ivan P. Fellegi and Alan B. Sunter, *A Theory for Record Linkage*, Journal of the American Statistical Association 64(328), 1969. <https://doi.org/10.1080/01621459.1969.10501049>
- [splink_docs] Ministry of Justice analytical services, *Splink documentation (version 5)*, living document. <https://moj-analytical-services.github.io/splink/>
