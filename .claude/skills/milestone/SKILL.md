---
name: milestone
description: Execute one NeonRadar build milestone (for example M1.4 or M2.3) end to end with the milestone protocol, open a pull request, and stop. Use when the user gives a milestone id.
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
   sub-milestone (M2.1, M2.3, M2.6 and M2.10 hold shared rules and build steps; 2.2 step 2).
2. Follow the milestone protocol in section 2.2 exactly: dependencies merged, plan (if the
   milestone says "Plan first"), branch, build, run every acceptance command, reviewer
   subagent, update PROGRESS.md, /open-pr, wait for CI, report, stop.
   If the milestone has a real-data run, follow step 6a of section 2.2: never run it unless
   the operator said in this session that the machine is approved; otherwise write the
   command into the pull request.
3. Never merge. Never start another milestone. If anything in section 2.5 applies, stop
   and ask.
