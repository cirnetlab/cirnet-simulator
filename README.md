# CIRNET Simulator

[English documentation](docs/en/index.md) · [Tài liệu tiếng Việt](docs/vi/index.md)

CIRNET Simulator runs deterministic digital and bounded DC models for CircuitGraph 1.0, 1.1, and 1.2. Its Python package is `cirnet-simulator==0.1.2` for Python 3.11 or later, with `cirnet-contracts==0.1.2`. Import `cirnet_sim`. The `netcircuit_sim` alias supports existing callers.

- `legacy` is the default and the backend selected for the published CIRNET 0.1.4 system profile. [Selected release manifest](https://github.com/cirnetlab/cirnet-remote/blob/38aea6120920f48cea817827ac2277cce4bef25e/integration/release-set.json)
- `cpp` is an opt-in digital and bounded DC backend in current source. It requires a separately selected C++ worker and its SHA-256. The r7 candidate passed Gate 1 on Windows x64. [Gate 1 decision](https://github.com/cirnetlab/cirnet-remote/blob/13a35145b6d15644c7be10d95a5410bf69e11867/docs/en/architecture/native-migration.md#gate-1-decision-for-windows-x64)
- `ngspice` is a reserved, unavailable selector for future analog and mixed-signal execution.

See [getting started](docs/en/getting-started.md), [backend selection](docs/en/backends.md), and [verification](docs/en/verification.md).
