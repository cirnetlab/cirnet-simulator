# Simulator repository work

- Simulator owns deterministic digital and bounded DC models and the private CNP1/CNP2 worker protocol. Coordinate protocol changes with Hardware. Contracts owns canonical schemas and catalogs. Remote selects system releases.
- Preserve simulation provenance, timing, resource limits and failure behavior. Keep unsupported analog and mixed-signal execution `UNAVAILABLE`.
- Use [Task Continuity](https://github.com/cirnetlab/cirnet-rules/blob/master/en/docs/distribution.md#task-continuity) for temporary plans, acceptance criteria and progress. Keep independent design specifications and durable plans in this repository and reference them from the checkpoint. Mark items complete after verification.
- Search for existing documentation. Update the authoritative page, consolidate overlap and verify both the [English](docs/en/index.md) and [Vietnamese](docs/vi/index.md) versions. Update the applicable [changelog](docs/changelogs/README.md).
- Distinguish `TARGET`, `IMPLEMENTED`, `TESTED`, `VERIFIED`, `RELEASED`, `UNAVAILABLE` and `BLOCKED`. Keep logs and build output in an owned external directory and retain approved summaries only.
- Follow the [verification guide](docs/en/contributing/verification.md). Review changes and ignored outputs. Stage, commit or publish only upon request.
