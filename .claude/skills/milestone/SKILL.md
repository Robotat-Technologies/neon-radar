---
name: milestone
description: Execute one NeonRadar build milestone (for example M2.3, M3.5a or M4.3a) end to end with the milestone protocol, open a pull request, and stop. Use when the user gives a milestone id.
argument-hint: "[milestone-id]"
disable-model-invocation: true
---
Execute milestone $ARGUMENTS.

Current state:
- Branch: !`git branch --show-current`
- Recent progress: !`tail -n 25 docs/build/PROGRESS.md 2>/dev/null || echo "PROGRESS.md missing"`

1. The spec is docs/build/PHASE-<n>.md where <n> is the number after "M". If you have not
   read its sections 0, 2, 3, 4 and 5 in this session, read them now. Then read only the
   section for $ARGUMENTS and whatever it links to, plus the parent section of a
   sub-milestone (M2.1, M2.3, M2.6, M2.10, M3.5 and M4.3 hold shared rules and build steps; 2.2
   step 2). For an M3.x id, also read the milestone's section of the code book,
   docs/build/PHASE-3-CODE.md (`## M3.x ...`; both parts of M3.4 use `## M3.4`), and
   docs/build/phase-3-reconciliation.md for every seam the milestone adapts (PHASE-3.md 2.10).
   For an M4.x id, read the milestone's section of docs/build/PHASE-4-CODE.md (`## M4.x ...`;
   M4.3a and M4.3b have their own) and docs/build/phase-4-reconciliation.md for every seam it
   adapts (PHASE-4.md 2.10), and append what you find there (2.2 step 2).
2. Follow the milestone protocol in section 2.2 exactly: dependencies merged, plan (if the
   milestone says "Plan first"), branch, build, run every acceptance command, reviewer
   subagent, update PROGRESS.md, /open-pr, wait for CI, report, stop.
   If the milestone has a real-data run, follow step 6a of section 2.2: never run it unless
   the operator said in this session that the machine is approved; otherwise write the
   command into the pull request.
   For an M3.x id, section 2.2 adds three steps:
   - 4a: copy the verbatim files before any other change, with
     `uv run python scripts/spec_extract.py extract --milestone M3.x --reference <scratch dir>`
     (M3.7, M3.8, M3.9 and M3.11 to M3.13 copy nothing), and commit them alone as
     `chore(<scope>): copy verbatim files from the code book [M3.x]`. Read the reference
     files in the scratch folder and write the adapters they describe yourself.
   - 6b: `uv run python scripts/spec_extract.py check --milestone M3.x` must pass; record a
     mechanical deviation in docs/build/phase-3-deviations.json (never for a test file,
     eval/baselines/ci.json or eval/freeze.json) and paste the check output into the PR.
   - 6c: for a detector, a query file or a `Source` implementation, run
     `NR_DETECT_SOURCE=neo4j uv run pytest detect/tests -m "not integration" -q` and, from
     M3.6 on, `uv run neonradar eval check`; paste both outputs into the PR.
   For an M4.x id, PHASE-4.md 2.2 adds the same steps with the Phase 4 book, and skips 4a and
   6b when the milestone's header says "Code book: none" (M4.7 to M4.10):
   - 4a: `make spec-extract M=M4.x REF=<scratch dir>`, committed alone as
     `chore(<scope>): copy verbatim files from the code book [M4.x]`.
   - 6b: `make spec-check M=M4.x` must pass; record a mechanical deviation in
     docs/build/phase-4-deviations.json (never for a test file, copilot/bench/,
     data/fixtures/copilot-bench/ or docs/benchmark-questions.md) and paste the output.
   - 6c: for a template, a sentence, a query file, a port or an operation: from M4.5 on
     `uv run neonradar copilot bench`; in M4.3b and M4.4
     `uv run pytest copilot/tests/test_benchmark.py -q`; from M4.4 on also
     `uv run pytest -m integration copilot/tests/test_neo4j_parity.py -q`. Paste the
     outputs into the PR under "Copilot sets".
   - M4.9 (2.2 step 4): never create its branch; the held-out owner has pushed it:
     `git fetch origin && git switch --track origin/p4/m4-9-heldout-figures`.
3. Never merge. Never start another milestone. If anything in section 2.5 applies, stop
   and ask. Never run `neonradar eval run --split test` or open data/cache/holdout (G11).
   Never read, run or tune against the held-out questions, open data/cache/heldout or run
   `neonradar copilot bench --file`, and never pull, install or switch on a model (G15, G16).
