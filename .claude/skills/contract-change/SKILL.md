---
name: contract-change
description: Prepare a change to a frozen NeonRadar contract (C1 record, C2 graph schema, C3 API, C4 alert) after tag contracts-v1.0.0. Use only when a contract-change issue exists.
argument-hint: "[issue-number]"
disable-model-invocation: true
---
1. Read issue #$ARGUMENTS. It must have the label contract-change and an approval comment
   from the tech lead. If not, stop.
2. Classify: patch, minor or major (PHASE-1.md 5.0). Major changes need written sign-off.
3. The guard hook blocks edits unless NR_ALLOW_CONTRACT_CHANGE=1 is set for this session.
   If edits are blocked, stop and ask the tech lead; never try to bypass the hook.
4. Change the models, bump the contract version, update contracts/CHANGELOG.md, run
   `make contracts` to regenerate JSON Schemas and OpenAPI, and for C2 add a NEW migration
   file. Update every consumer and test in the same PR.
5. Run `make check` and `make test-int`. Open the PR with the label contract-change.
