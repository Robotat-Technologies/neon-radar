"""The data manager (PHASE-2.md M2.2): profiles, folders, the real-data gate, downloads, retention.

One place decides which data a profile loads (`profiles`), whether it may run on this machine
(`gate`), where it goes (`layout`), how it is downloaded (`sources`, `download`), how long it
stays and how it is deleted (`retention`, `purge`). Loaders plug in through `sources`.
"""
