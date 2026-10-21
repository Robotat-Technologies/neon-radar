# Approved real-data machines

The data steward keeps this list (PHASE-2.md 1.1 and 7.4; [real-data handling](real-data-handling.md)). Only a machine listed here may load a real profile (`uk-tiny`, `uk-sample`) or run the real-data instance `neo4j-real`, and only its owner sets `NR_REAL_DATA_MACHINE=approved` in that machine's `.env`, after the row is merged.

A machine qualifies when full-disk encryption is switched on (FileVault on macOS, BitLocker on Windows, LUKS on Linux) and the screen locks. GitHub Codespaces, CI runners and cloud sessions never qualify. Record no serial numbers or other device identifiers: a nickname is enough.

When a machine stops being used for real data, its owner runs `uv run neonradar data purge --all-real --graph --yes` (M2.2), removes `NR_REAL_DATA_MACHINE=approved` from its `.env`, and the data steward deletes its row.

| Handle | Machine nickname | Disk encryption | Screen lock | Checked on | Checked by |
|---|---|---|---|---|---|
