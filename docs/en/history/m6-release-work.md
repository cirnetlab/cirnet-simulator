# CIRNET repository rename verification

Date: 2026-10-29, Asia/Saigon. Current repository is [CIRNETLAB/CIRNET-Simulator](https://github.com/CIRNETLAB/CIRNET-Simulator). Local checkout names remain unchanged. README authority links retain their original source revisions; package metadata and the workflow display name now use CIRNET. Python/npm identifiers, exact dependency versions, environment names, schemas, backend identities, all nine runtime modules and LICENSE are unchanged. The workflow explicitly passes `-B` in isolated tests.

Local verification used fresh external tracked-file exports of uncommitted changes over `ff63616a7a8c5d3f65e60cdb85db2b4b4ab42fa7`, Windows/Python 3.12.12/Node 24.20.0. Export fingerprint before adding this record: `a6d0e9cd73683204c009ad4b36aa937a1b07d2e08107c6c9f546ad4ed99a19b4`. This is not evidence of a committed clean checkout or hosted CI for the eventual rename commit. The README release instruction was clarified after this candidate build; the final committed-source build must verify that later documentation input as well.

| Gate | Result |
| --- | --- |
| Direct final-name anonymous downloads | PASS: exact released Contracts/DEV/Simulator/Hardware numeric asset URLs and selected digests, without credentials. |
| Fresh standalone environment | PASS: SHA256-locked third-party closure downloaded, then installed offline; first-party wheels selected by digest, no sibling/editable/runtime source imports. |
| Published-wheel baseline | PASS: 110 tests, 34.89 seconds, external CWD. |
| Candidate wheel/sdist | PASS: built without network isolation from the independent export; fresh sdist rebuild reproduces wheel bytes with `SOURCE_DATE_EPOCH=1793119595`. |
| Installed candidate | PASS: forced exact-wheel reinstall, `pip check`, archive/RECORD/resource/import provenance; 110 tests, 25.96 seconds, `python -I -B -m pytest`. |
| Byte comparison | PASS: wheel inventory, all runtime payloads, dependencies, version and LICENSE unchanged; only METADATA/RECORD change. Sdist changes are current README, verification policy, workflow and package metadata. |
| Workflow validation | PASS: official actionlint 1.7.12, `-shellcheck= -pyflakes=`. |
| Committed-source/master hosted CI | NOT_RUN in this local work unit; release owner verifies after integration. |

Published wheel SHA256 remains `78b857369baec88800d08e37977afacca3321decd05b6cd50ea925c033ea7b89`; candidate wheel is `fb91875f613a136a1ad9e2bab976e4016c52f5efafc444715d95ef325a2a639f`. Candidate sdist is `e0eee3633167fe5e4c2899435a46ab410ab49bf0c727d9b787b541c0736dbd59`. These are distinct same-version archives. The immutable v0.1.1 tag/assets retain original provenance and were not replaced or retagged. Current metadata does not imply that published bytes were rebuilt from a rename commit.

Inspected external evidence: `current-name-hardware-simulator-b9fa2760/VERIFICATION_RECEIPT.json` SHA256 `bb6a6b38f0c06e8ea6d96a7c806dfe78066e07a68699706f96eaa52da89d36c4`, and `ARTIFACT_COMPARISON_RECEIPT.json` SHA256 `a2384262a4dd9f13fe8745f274fe5d433377565afa6f72ec50148b29b4e92b84`, under the migration owner's canonical external session. The receipt preserves an initial operator-only checker launch failure: `-I` hid its helper directory; the documented `python -B scripts/check_installed.py` invocation passed without source changes. Historical file and LICENSE physical hashes/normalized Git blobs match; original ignored-output lists are unchanged. This leaf task did not stage, commit, push or publish; shared-session inspection/cleanup remains with its owner. No native ngspice/analog availability or deployed-system readiness follows from these tests.

The dated work record below is preserved as historical evidence.

---

# M6 product version work

Date: 2026-10-27. This is current work-unit evidence, separate from historical migration reports.

Python metadata, Contracts dependency, installed-wheel checker, selected-wheel metadata prefix, installer filenames, consumer tests, CI and current documentation target product 0.1.1 and Contracts 0.1.1. DEV remains 1.0.0a1. Backend adapter/plan identity, schema and simulation semantics are unchanged. Historical pre-facade Simulator artifacts that also used 0.1.1 remain distinct by SHA256; rollback must identify the exact payload and matching consumer implementation.

Changed Python/JSON/TOML syntax checks PASS. Installed-artifact/runtime/spawn acceptance is NOT_RUN in this work unit until committed Contracts and Simulator artifacts are rebuilt. No package installations or historical report changes were performed.

Use README bootstrap/locked closure commands, then `python -m build --no-isolation --outdir ABSOLUTE_SESSION/dist`; force-install `netcircuit_simulator-0.1.1-py3-none-any.whl`, run `pip check`, `scripts/check_installed.py --wheel ABSOLUTE_WHEEL`, and external-CWD `python -I -B -m pytest ABSOLUTE_TESTS --basetemp ABSOLUTE_SESSION/pytest`. Preserve exact manifest/digest provenance; no sibling runtime source is needed.

All generated regression fixtures/archives used the shared external allocator session with all six Git roots. Shared-session cleanup remains with the migration owner. No stage/commit/merge/push was performed by this work unit.
