# Repository work

Start with the [current English documentation](docs/en/index.md). Update its
Vietnamese counterpart in the same documentation change.

Read the [repository overview](README.md) and [verification guide](docs/en/contributing/verification.md) before changing source. Runtime models consume versioned Contracts. Do not copy canonical schemas or catalogs here. Preserve Lab-First safety and unavailable-model behavior.

All logs, traces, raw diagnostics and temporary verification output must begin outside every checkout/worktree/Git directory using the pinned canonical DEV allocator. Only Markdown verification evidence belongs here. Inspect before guarded cleanup. Preserve source assets, historical Markdown, LICENSE and source provenance. Do not stage/commit/push without user authorization.
