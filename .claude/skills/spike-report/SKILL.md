---
name: spike-report
description: Write a data source spike report in docs/data/spikes from the measured results of a spike run. Use at the end of an M1.8 spike.
argument-hint: "[source-slug]"
---
Write docs/data/spikes/$ARGUMENTS.md with these sections:
1. Command run, date, duration, network conditions.
2. What was fetched (endpoints or files, record counts by FtM schema). No personal data:
   counts, field names and coverage only.
3. Measured facts that confirm or correct docs/research/2026-10-16/ (sizes, headers, rate
   limit behaviour, redirects, encodings).
4. Mapping notes: source field to FtM property, and anything that does not map.
5. Licence and personal-data notes for the data steward.
6. Gotchas and recommendations for the Phase 2 loader.
7. Verdict: go, go with changes, or drop (the plan's day-2 spike rule).
