# CIRNET-Simulator

Repository: [CIRNETLAB/CIRNET-Simulator](https://github.com/CIRNETLAB/CIRNET-Simulator). Existing local directories may retain the `net-Circuit-Simulator` name. Canonical Python imports use `cirnet_sim`; `CIRNET_*` settings take precedence over legacy `NETCIRCUIT_*` aliases. Legacy imports remain compatible.

Independent `cirnet-simulator==0.1.1` with replaceable simulation backends, Python >=3.11, consuming `cirnet-contracts==0.1.1`. The canonical Python namespace and public preview/dispatch imports use `cirnet_sim`; the small `netcircuit_sim` shim aliases the same modules and classes for existing consumers. Release artifacts are wheel and sdist. Revalidate the existing immutable `v0.1.1` artifacts under the current repository URL while retaining their original source revisions and SHA256. Compare candidates from changed source separately; changed published bytes or tags require an explicit release decision and must respect immutability. Record the selected artifacts in the system manifest. No sibling checkout or API/Web implementation is required.

Supported CircuitGraph 1.0/1.1/1.2 passes offline schema/authoring validation and explicit domain dispatch into deterministic event simulation. Models retain switch/input, AND/74HC08, NOT, OR/XOR, LED/probe, clock and the bounded powered-HC08/source/resistor/LED DC subset. Known board/instrument visuals create no electrical nets. Unknown models are UNEXECUTABLE. Analog/SPICE/mixed adapters remain UNAVAILABLE without fabricated samples.

Time is integer nanoseconds; default digital delay is an educational 8 ns model, not measured component timing. Floating inputs remain X. Changes at one timestamp settle before capture with stable ordering. Captures hold actual 0/1/X transitions, at most four requested probes. Default software budgets are 1 ms, 100,000 scheduled events and 100,000 captured samples. The supported scheduling limit up to 1,000,000 is distinct from the fixed capture bound; exceeding either fails without truncation.

Hardware owns the bounded worker pool, RPC sessions and stop/reset generation invalidation. Remote owns REST previews, auth/persistence and integrated acceptance. Canonical architecture remains [Lab-First](https://github.com/CIRNETLAB/CIRNET-Remote/blob/25d2e6784035f6a8165142f8a8e03c4534512bcc/docs/ARCHITECTURE.md); [signal-domain authority](https://github.com/CIRNETLAB/CIRNET-Remote/blob/25d2e6784035f6a8165142f8a8e03c4534512bcc/docs/architecture/signal-domains-and-simulation.md) defines current model boundaries. The pinned authority revision is unchanged by the repository rename.

## Build and verify

Build the current source in a fresh environment with the reviewed
`cirnet-contracts==0.1.1` wheel. The immutable Simulator release keeps its
original `netcircuit-contracts==0.1.1` dependency and uses a separate
environment. Both Contracts distributions install the `contracts` namespace.

Use Node 26 and Python 3.14 in CI (Python >=3.11 supported). Select the reviewed Contracts artifact manifest, which contains exact wheel and DEV paths/SHA256. A fresh Python environment should live outside the checkout. The exact third-party closure is in requirements-verification.lock. Set TMP/TEMP/TMPDIR and pip cache inside the owned session before subsequent commands that create temporary diagnostics. Read [verification policy](docs/VERIFICATION.md).

PowerShell, starting in this repository with the intended Python environment active:

```powershell
$env:CIRNET_CONTRACTS_ARTIFACT_MANIFEST = 'C:/absolute/release/artifacts.json'
$bootstrap = python -c "from scripts.bootstrap_contract_tools import bootstrap; import json; value=bootstrap(); print(json.dumps(value))" | Select-Object -Last 1 | ConvertFrom-Json
$env:CIRNET_ARTIFACTS_SESSION = $bootstrap.session
$env:CIRNET_ARTIFACTS_CONTEXT = $bootstrap.context | ConvertTo-Json -Compress -Depth 10
$env:TMP = $env:TEMP = $env:TMPDIR = $bootstrap.session
$env:PIP_CACHE_DIR = Join-Path $bootstrap.session 'pip-cache'
python -m pip install --require-hashes --only-binary=:all: -r requirements-verification.lock
python scripts/install_contracts.py
$env:SOURCE_DATE_EPOCH = git log -1 --format=%ct
python -m build --no-isolation --outdir "$env:CIRNET_ARTIFACTS_SESSION/dist"
python -m pip install --no-deps --force-reinstall "$env:CIRNET_ARTIFACTS_SESSION/dist/cirnet_simulator-0.1.1-py3-none-any.whl"
python -m pip check
python scripts/check_installed.py --wheel "$env:CIRNET_ARTIFACTS_SESSION/dist/cirnet_simulator-0.1.1-py3-none-any.whl"
$product = (Get-Location).Path
Push-Location $env:CIRNET_ARTIFACTS_SESSION
python -I -B -m pytest "$product/tests" --basetemp "$env:CIRNET_ARTIFACTS_SESSION/pytest"
Pop-Location
# Inspect results before guarded cleanup; keep artifacts selected for publication separately.
node scripts/artifact-paths.mjs --cleanup $env:CIRNET_ARTIFACTS_SESSION
```

CI builds the renamed Contracts wheel from the commit and SHA256 source archive pinned in `integration/ci-source-dependencies.json`. The build and its hash-locked toolchain stay inside the owned external session. Local installs use an explicit reviewed wheel selection. The independent DEV wheel still uses its configured URL and SHA256. Public published assets support anonymous access; authenticated CI/draft access still uses the selected-repository read token. Only GitHub release-asset API requests receive credentials; redirects do not. Missing pins fail closed. No package is published automatically. Offline verification downloads the SHA256-locked closure into a wheelhouse, then installs with `--require-hashes --only-binary=:all: --no-index --find-links ABSOLUTE_WHEELHOUSE`; first-party artifacts remain selected by reviewed digest.

The existing immutable [v0.1.1 release](https://github.com/CIRNETLAB/CIRNET-Simulator/releases/tag/v0.1.1) retains its original tag, artifact bytes and source provenance. A build from renamed current-source documentation/metadata is a separate candidate even when its package version is 0.1.1; it must not replace those published bytes or be attributed to the original tag. See [release verification work](docs/M6_RELEASE_WORK.md).

## Compatibility and rollback

The canonical `cirnet_sim.backends` facade retains the legacy runtime algorithms extracted from Remote revision 25d2e6784035f6a8165142f8a8e03c4534512bcc. Existing Graph 1.0/1.1/1.2, model selection, descriptor identity, version pins, legacy import aliases and numeric bounds remain compatible. Tests load shared fixtures from installed Contracts resources. API and Hardware consumers must both pin Simulator 0.1.1 and Contracts 0.1.1.

Rollback restores the prior compatible Simulator/Contracts wheels and consumer dependency pins. No stored graph/capture/data conversion is part of M3. Original Remote source is retained as frozen provenance/rollback material. Git history extraction/mapping, ancestry reachability and integrated acceptance are recorded by the migration release process; historical extraction reports preserve their original results.


## Replaceable backend boundary

`CIRNET_SIMULATION_BACKEND` selects the configured built-in core: `legacy` by default, or the reserved `ngspice` adapter. Application Settings and Hardware stations snapshot this choice at creation. Documents and graph properties cannot select a core. Ngspice currently reports unavailable with no digital/analog/instrument channels: no executable is searched, no DLL is loaded and no process or invented sample is produced. Existing digital/DC features continue through `legacy`. The original `engine` and `dispatch` APIs remain legacy compatibility entrypoints.

Use `cirnet_sim.backends.select_backend_id()` once, then pass the returned ID explicitly to `compile_graph(graph, backend_id=...)` and `preview_physical_graph(graph, backend_id=...)`. Submit the resulting `CompiledPlan` to the module-level `backends.run_plan(plan, capture_config, vectors, clock_config, inputs)` worker function. Its immutable backend identity contains ID, adapter version and plan format; execution resolves this identity rather than environment selection. Unknown/mismatched providers fail without fallback. `.directions` remains a read-only endpoint mapping for Hardware admission.

Trusted application code may compose `BackendRegistry([provider, ...])`. A provider exposes a frozen `BackendDescriptor` and implements `compile`, `execute`, and `preview`. Compile returns a process-serializable payload with a directions mapping and all execution-relevant configuration frozen into that payload. Execute must use that configuration rather than re-read the environment. Registry membership and descriptor snapshots are immutable; duplicate IDs, mutated descriptors, identity/version mismatches and nonserializable plans are rejected. Unexpected provider bugs remain errors. There is no automatic Python plugin discovery or module-path loading.

The current Hardware service composes built-ins only. A future custom worker must explicitly construct the same trusted provider registry in every spawned process and pass it to `run_plan(..., registry=...)`; registration in a parent process is not sufficient. Backend identity describes the adapter/plan interface, not an implemented ngspice ABI or model digest. Native payload ABI, pinned native builds/model artifacts, cancellation acknowledgment and typed analog results are future integration work. Current capture Contracts are digital and remain unchanged.

For rollback, select `legacy` within this release, or restore the historical pre-facade artifacts together with their matching consumer code and dependency pins. Historical artifacts sharing the 0.1.1 version remain distinct by archive SHA256; version alone is insufficient. Consumers importing this facade require the matching artifact payload. No document/capture migration is required.

Current-source builds produce CIRNET-named distributions. Existing published `netcircuit-*` wheels, their source revisions and hashes remain immutable; use separate environments for those historical artifacts. DEV tooling accepts the distribution/resource name selected by its exact release lock.
