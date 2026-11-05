# Learning log: @mukhlif-aljabri07


| | |
|---|---|
| Name |Mukhlif Muhammed Aljabri|
| Squad |Not assigned yet  (interested in Typologies & Detection)|
| Roles |Intern|
| Started |2026-10-15|

## Skills self-assessment

Score yourself from 1 to 5 with the scale in [skills-self-assessment.md](skills-self-assessment.md): "Start" in your first week, "End" in the final week, "Change" is End minus Start.

| Skill | Start | End | Change |
|---|---|---|---|
| Graph modelling |3 | | |
| Cypher |4 | | |
| Entity resolution |3 | | |
| AML domain knowledge |4 | | |
| Vue | 2| | |
| Docker |3 | | |
| Code review |3 | | |
| Working effectively with AI |4 | | |

## Log

One entry a week, newest at the bottom: three to five lines on what you read, what you built, what you got wrong and what still confuses you.


### Week of 2026-10-19

- Read: The NeonRadar SRS (detection, evaluation, contracts)
- Built: I worked on building a small repo called mini-radar on Aura that has a fixture with a crime loopand a look-alike and a circular flow query with $window_days and a python function and alert_id with sha256,and a template headline and a lint.
- Got wrong: The fixture's amount as text ,and the look-alikes dates running backwords.
Forgetting sorted (the same crime would get two ids)   
- Still confused by: Why a detector isn't "trained" , and what pattern strength means.

### Week of 2026-10-26

- Read: The team guide ,and assignment 1 + 2 file descriptions on the terminal,read the real expected.json (cases A–E, one rule broken per case).
- Built: Ran the neonradar project from scratch on Windows,ran the project's test(30 passed),wrote Query A (WITH + collect(), after count() in WHERE failed) and a first Query B with a variable-length path,wrote the circular_flow query,understood the 6 rows (rotations), all() + range(), the forgotten .date, the window check outside all(), and :param.
- Got wrong: A broken test slipped into main, so i made a fix PR,make setup failed on pyicu: Python.h was missing, fixed with python3.14-dev,port 8080 taken, fixed with NR_UI_PORT=8081.
- Still confused by:Docker in general and, when to use a fork vs pushing a branch

### Week of 2026-11-02
- Read: The explainer and definition files of assignment 2 typologies, the sources "fatf_egmont_tbml_indicators_2021","fatf_egmont_concealment_2018","ffiec_appendix_f", "fatf_pml_2018" links ,the Assignment 1 file.
- Built: Assignment 1 (the shared-director query) the T1, T2 and T6 videos,the T1->T11 except T8 todo tasks, Assignment 2 
- Got wrong: The separate query creating 15 empty nodes (an undefined c),duplicate pairs, the OnCompany typo returning 0 rows silently.
- Still confused by: how D6 reviews will work.