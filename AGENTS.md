# Repository work

- Start with the [English index](docs/en/index.md). After verification, update affected English and [Vietnamese](docs/vi/index.md) pages and the [changelog](docs/changelogs/README.md).
- Keep each task plan only in `.superpowers/plans/` and its matching spec, acceptance criteria and progress checklist only in `.superpowers/specs/`. Keep open items as `- [ ]` and use `- [x]` only after verification.
- Simulator owns deterministic digital and bounded DC models and private CNP1/CNP2 worker framing. Coordinate worker protocol changes with Hardware. Preserve the `legacy` default and Lab-First unavailable-model behavior, including zero samples for unavailable `ngspice`.
- Use pinned Contracts artifacts and preserve the `cirnet_sim` and `netcircuit_sim` compatibility boundary. Keep canonical schemas and catalogs in Contracts, station lifecycles in Hardware and REST orchestration in Remote.
- Follow the [verification guide](docs/en/contributing/verification.md). Generate raw evidence with the pinned DEV allocator outside every checkout, worktree and Git directory. List the owner and all participating roots. Keep Markdown evidence in the repo. Inspect evidence and clean only owned sessions.
- Verify claims against source, Contracts and tests. Preserve assets, fixtures, licenses and historical evidence. Review Git diff, status and ignored outputs. Stage, commit, merge, push or publish only with explicit authorization.
