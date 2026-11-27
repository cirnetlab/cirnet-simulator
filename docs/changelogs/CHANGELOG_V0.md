# CIRNET Simulator version 0 changelog

[Changelog index](README.md)

## Unreleased

### Changed

- Standardize English major-version changelog navigation.

## v0.3.0-dev.1 — Development

Git tags and GitHub Releases provide no publication date for this development version.

### Added

- Added Windows x64 build, install and protocol verification.

### Changed

- Moved the digital event solver into a private worker module and linked the source responsibilities in both backend guides.
- Migrated the C++20 worker, bounded DC and CNP1/CNP2 regression tests.
- Documented the repository-local worker regression fixtures and the provenance of their powered-device and timing expectations.
- Linked the worker boundary to CIRNET Lab-First execution and acceptance requirements.

### Fixed

- Recovered worker regressions for breadboard net fan-out, same-time input and probe order, and powered 74HC08 DC LED states.

**Source**

- [Native implementation baseline](https://github.com/cirnetlab/cirnet-simulator/commit/e060062f5c81e0eee126f6ddd1d797d33e75e20f)
