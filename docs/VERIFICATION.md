# Simulator verification

## 2026-11-05 Python 3.14 compatibility

Primary CI and local verification now use normal-GIL CPython 3.14; reusable
package metadata retains its 3.11+ compatibility. A fresh Windows AMD64 3.14.6
environment passes all 121 installed-wheel tests and original archive/RECORD
provenance checks. Its independently extracted sdist rebuilds to the same
candidate wheel bytes. The existing hashed binary dependency closure already
admits the selected 3.14 Windows and glibc Linux wheels.

Independent native Linux 3.14.6 verification passes all 122 installed tests,
including the added CI selection guard and actual DEV bootstrap. Fresh Linux
wheel/sdist builds, selected wheel provenance and `pip check` pass. The pinned
Contracts helper is also exercised end-to-end under 3.14 with its SDK build.

The source CI helper adds only reviewed 3.14 wheel hashes to the pinned
Contracts build copy, after checking both original lock digests and every
existing exact package version. Eleven focused positive/negative profile tests
pass, including traversal, wrong-source and version/hash rejection before
writes. Original source pins and package versions are unchanged. Raw evidence
starts outside Git in the session owned by `cirnet-python314-compat-20261105`.
Hosted Actions, browser acceptance and publication are NOT_RUN for this upgrade.

## 2026-11-05 Node 26 LTS CI baseline

Current CI selects Node 26 LTS before allocator bootstrap. Both tests in
`tests/test_bootstrap_environment.py` pass with portable Node 26.13.0 on PATH;
actionlint 1.7.12 passes the workflow with `-shellcheck= -pyflakes=`. This changes
the verification toolchain only. Runtime Python source, dependency locks and
published artifacts are unchanged. The full installed-wheel/backend gate and
hosted Actions are NOT_RUN for this policy change. Historical results below
retain their recorded Node versions. Evidence was inspected in the shared
external session owned by `cirnet-node26-compat-20261105`.

Current repository identity is [CIRNETLAB/CIRNET-Simulator](https://github.com/CIRNETLAB/CIRNET-Simulator); local `net-Circuit-*` directory names and dated extraction/provenance records remain valid. Current-source CI builds the renamed Contracts wheel from the exact Git commit and SHA256 source archive in `integration/ci-source-dependencies.json`. Keep immutable v0.1.1 source/tag/artifact provenance separate from candidates rebuilt after documentation or package metadata changes. Pass `-B` explicitly to isolated Python tests because `-I` ignores the environment's bytecode setting.

Select the exact `cirnet-contracts==0.1.1` and DEV 1.0.0a1 wheel artifacts by SHA256 in a fresh environment. scripts/bootstrap_contract_tools.py, artifact_download.py, contracts_artifact.py and allocator adapters originate from Remote revision 25d2e6784035f6a8165142f8a8e03c4534512bcc. DEV source uses `cirnet-artifact-paths` and `cirnet_artifact_paths`; the exact reviewed lock still selects the immutable legacy `netcircuit-artifact-paths` wheel. The canonical allocator implementation belongs exclusively to that installed DEV artifact; these adapters validate and delegate to it. Canonical DEV selection requires a matching reviewed wheel/Node lock.

Set CIRNET_ARTIFACTS_CONTEXT before bootstrap when several repositories participate. The JSON object contains an owner and every participating absolute Git root. Standalone verification defaults to this repository only. Keep the identical context for children and cleanup.

Bootstrap writes the ownership/session to GITHUB_ENV immediately after allocation so CI can clean even after installation failure. Capture all local command output under that owned session. Do not run pytest with cacheprovider or default source-local temporary output. Build caches are compiler output; diagnostics are always external.

Run tests against the built wheel from an external working directory using `python -I -m pytest --import-mode=importlib ABSOLUTE_TESTS --basetemp OWNED_SESSION/pytest`. `scripts/check_installed.py --wheel ABSOLUTE_NEWLY_BUILT_WHEEL` binds verification to the selected archive SHA256, payload and original RECORD entries. Always force reinstall when rebuilding the same package version. The checker also rejects editable installs, source shadowing and modified RECORD-owned payloads. It verifies the installed Contracts resource owner as well. Runtime source must not enter PYTHONPATH.

Check the wheel inventory (nine canonical runtime modules, one legacy import shim and distribution metadata), sdist fixture/tooling presence, dependency closure with `pip check`, and fresh installation without source/editable dependencies. Worker lifecycle, REST preview and Hardware virtual integration stay in Remote.

After inspecting diagnostics and verifying owned child processes exited, clean only this session using `node scripts/artifact-paths.mjs --cleanup ABSOLUTE_SESSION`. Never remove an arbitrary parent or another session. Preserve shared integration sessions for their owner to clean. No full browser result or physical hardware availability follows from these package tests.


Backend verification additionally covers legacy compile/run/preview parity, permissive unsupported previews, truthful ngspice unavailability without native launch, trusted provider delegation, immutable identity/directions/registry snapshots, source-independent pickle/spawn execution, and rejection of missing/mismatched providers without fallback. The current Hardware composition permits built-ins only; custom extension tests compose a trusted registry explicitly in the child. Preserve historical baseline artifacts by exact digest while validating the current 0.1.1 artifact; no native integration or analog capability is established by these tests.


## 2026-11-04 canonical naming verification

PASS on Windows, Asia/Saigon (+07:00), with Python 3.14.4, Node 24.20.0,
pytest 9.1.1 and actionlint 1.7.12. CI continues to pin Python 3.12 and Node 22;
this local run does not claim a Linux CI result. Verification used fresh external
source exports and a fresh virtual environment with the complete hash-locked
Hardware verification closure. The exports were uncommitted inputs based on
`f04bb9e4fcd39803de62ae9c3c305206c07e6255`; they are distinct from a future committed checkout and immutable
published releases. `SOURCE_DATE_EPOCH=1793782800` was explicit.

The selected `cirnet-contracts==0.1.1` wheel SHA256 was
`2ba8cd1a3c1aeb02c10c154a5e3d8b169e96f4caee4c332d4a1bbc88d9ff2e1a`.
The immutable DEV wheel remained selected by its existing SHA256
`ff76532c69b2115338edb641660c966c5459dd40cb806f52a1e2e8c379c70a1f`;
actual canonical-environment bootstrap, installation and allocator integrity
checks passed with that legacy artifact. No published artifact or historical
provenance lock was changed.

`cirnet_simulator-0.1.1-py3-none-any.whl` SHA256:
`8865ba5c120ccf6c41bb7f2f7927d092dcccbf5c79146118353b0a542b583cb2`.
The wheel contains nine canonical runtime modules and one legacy import shim,
with 15 total archive members including distribution metadata. All **118 tests
passed** in the final installed-wheel run. Coverage includes both import orders,
module/class identity, historical pickle module paths, actual spawned execution
of a legacy-named serialized plan, canonical environment precedence and legacy
fallback, deterministic legacy simulation and truthful unavailable backends.

Isolated test probes now pass `-B` explicitly. Their four newly created source
bytecode files were inspected and guarded-cleaned before the final run. The eight
pre-existing test bytecode files dated 2026-10-27 were preserved; the final run
created no additional source bytecode.

`python -m pip check` and the newly selected wheel's
`scripts/check_installed.py --wheel ABSOLUTE_WHEEL` passed after force reinstall.
Tests ran from the external working directory using
`python -I -B -m pytest ABSOLUTE_TESTS --basetemp OWNED_SESSION/PRODUCT-pytest-final-triplet`.
The changed workflow passed actionlint 1.7.12 with `-shellcheck= -pyflakes=`;
canonical CI secrets/variables retain explicit legacy fallbacks, including SHA256.
The official Windows actionlint archive SHA256 was
`6e7241b51e6817ea6a047693d8e6fed13b31819c9a0dd6c5a726e1592d22f6e9`.

Raw build/install/test diagnostics began under the allocator-owned shared session
`C:/Users/trann/.codex/visualizations/2026/10/28/01a184f1-bcd8-7171-94bd-3a3cef062860/netcircuit-zw1kOX/python-leaves`.
The session owner retains it for integrated review and cleanup. Frozen fixtures,
historical Markdown and published release inputs were preserved. These checks do
not establish physical hardware availability, electrical safety certification,
native SPICE integration or analog capability.

### Final namespace and allocator follow-up (2026-11-04)

All 120 tests pass against Contracts wheel `e129eb9075083dccbce9a37a595abe04f405197c2c06a86e651cb47b9a8acead` and Simulator wheel `8865ba5c120ccf6c41bb7f2f7927d092dcccbf5c79146118353b0a542b583cb2`, after the required pinned DEV bootstrap. This includes both allocator alias regressions. The source CI pin now selects verified Contracts commit `3dea0a64c5f79d9c2cca0400d39643135d5bc9ab`; every downloaded archive file matched its committed Git blob. Final raw diagnostics use the external `netcircuit-cKRGky` session; initial shared diagnostics were partially removed by a Remote fixture isolation regression that has been corrected. Git history, frozen inputs and user data are unchanged.
