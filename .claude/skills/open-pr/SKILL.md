---
name: open-pr
description: Push the current branch and open a NeonRadar pull request with the template, labels and human owner, after checks pass. Use at the end of a milestone.
---
1. Confirm `make check` passed in this session (run it if not). Confirm the milestone's
   acceptance commands passed.
2. `git push -u origin <current branch>`.
3. Write the PR body from .github/pull_request_template.md: summary, milestone, human owner
   (from docs/build/project.yaml: the squad mentor, or the tech lead for repo and contract
   work), acceptance evidence (commands and key output lines), contract impact, data and
   licence impact, AI involvement (agent), deviations from spec, not addressed.
4. `gh pr create --base main --title "<type>(<scope>): <summary> [<milestone>]"
   --body-file <tmp file> --label agent --label phase-<n> --label <squad labels>`, plus
   `--label size-exception` only when the milestone header says `Size: exception`.
5. Print the PR URL. Do not merge.
