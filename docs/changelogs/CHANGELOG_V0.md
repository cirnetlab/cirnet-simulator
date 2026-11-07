# CIRNET Simulator changelog for major version 0

[Changelog index](README.md) · [English history](../en/history/index.md) ·
[Lịch sử tiếng Việt](../vi/history/index.md)

## Contents

- [Unreleased](#unreleased)
- [v0.1.2](#v012)
- [v0.1.1](#v011)

## Unreleased

### Added

- Added the opt-in `cpp` backend with a separately selected worker and
  SHA-256 pin. Its private CNP1/CNP2 framing supports deterministic digital
  and bounded DC execution. The r7 candidate passed Gate 1 on Windows x64.
  The published CIRNET 0.1.4 profile selects `legacy`; SPICE and physical HIL
  remain `NOT RUN` for the candidate. [Worker source](https://github.com/cirnetlab/cirnet-simulator/commit/19c24be6f3cfc543efe6464a482607fb226dc171) · [Backend scope and Gate 1 evidence](../en/architecture/backends.md)

### Changed

- Organized the release changelog by major and documented how to maintain
  paired guidance and preserve historical records. Moved the ngspice
  implementation plan and acceptance checklist to local task records and kept
  the verified source inputs in the paired docs. [Documentation conventions](../en/contributing/writing-documentation.md) · [ngspice research](../en/architecture/ngspice-integration.md)

## v0.1.2

Published **2026-11-05** at `15:56:09 +07:00`. Lightweight tag target
`9ec36fa` at `15:54:44 +07:00`.
[GitHub release](https://github.com/cirnetlab/cirnet-simulator/releases/tag/v0.1.2) · [Tagged source](https://github.com/cirnetlab/cirnet-simulator/tree/9ec36fa2772ba8227e15ae33fec9710943a9a775) · [System selection](https://github.com/cirnetlab/cirnet-remote/blob/38aea6120920f48cea817827ac2277cce4bef25e/integration/release-set.json)

### Changed

- Published `cirnet-simulator==0.1.2` with an exact
  `cirnet-contracts==0.1.2` dependency. Canonical imports use
  `cirnet_sim`. The `netcircuit_sim` shim preserves module and class
  identity for existing callers. [Tagged package metadata](https://github.com/cirnetlab/cirnet-simulator/blob/9ec36fa2772ba8227e15ae33fec9710943a9a775/pyproject.toml) · [Namespace compatibility change](https://github.com/cirnetlab/cirnet-simulator/commit/b2bfe2c0ff5ca05ede19122830de21f97a2cecd2)
- Adopted canonical `CIRNET_*` settings with precedence over legacy
  `NETCIRCUIT_*` aliases. The `legacy` backend remains the default and
  `ngspice` remains unavailable. [Tagged runtime guidance](https://github.com/cirnetlab/cirnet-simulator/blob/9ec36fa2772ba8227e15ae33fec9710943a9a775/README.md)
- Moved CI to Node.js 26 and Python 3.14. The package still supports
  Python 3.11 or later. [Verification record](../en/history/verification-ledger.md#2026-11-05-python-314-compatibility)

## v0.1.1

Published **2026-10-28** at `22:51:23 +07:00`. Annotated tag
`90fd9ed` at `22:50:15 +07:00`, targeting `ff63616` from
`2026-10-27 at 23:46:35 +07:00`.
[GitHub release](https://github.com/cirnetlab/cirnet-simulator/releases/tag/v0.1.1) · [Tagged source](https://github.com/cirnetlab/cirnet-simulator/tree/ff63616a7a8c5d3f65e60cdb85db2b4b4ab42fa7) · [System selection](https://github.com/cirnetlab/cirnet-remote/blob/065179ead7c7cf4f44483b74edca99bb84f8f2a5/integration/release-set.json)

### Added

- Published the first immutable wheel and source distribution as
  `netcircuit-simulator==0.1.1`. Its `netcircuit_sim` namespace uses
  `netcircuit-contracts==0.1.1` and supports deterministic digital and bounded
  DC execution for CircuitGraph 1.0, 1.1 and 1.2. [Tagged README](https://github.com/cirnetlab/cirnet-simulator/blob/ff63616a7a8c5d3f65e60cdb85db2b4b4ab42fa7/README.md) · [M3 extraction record](../en/history/extraction-history.md)
