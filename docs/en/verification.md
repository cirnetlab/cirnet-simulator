# Verify the Simulator wheel

English · [Tiếng Việt](../vi/verification.md)

[Documentation index](index.md)

Use Node 26 and Python 3.14 to reproduce current CI. Activate a fresh Python environment outside all checkouts. Select the reviewed Contracts 0.1.2 wheel and the pinned DEV allocator. Run from the Simulator repository in PowerShell and replace the manifest path with a reviewed absolute path.

Run the commands in order and stop at the first failure.

~~~powershell
$env:CIRNET_CONTRACTS_ARTIFACT_MANIFEST = 'C:/absolute/contracts/artifacts.json'
$bootstrap = python -B -c "from scripts.bootstrap_contract_tools import bootstrap; import json; print(json.dumps(bootstrap()))" | Select-Object -Last 1 | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or -not $bootstrap.session -or -not $bootstrap.context) {
    throw 'Could not allocate a verification session.'
}
$env:CIRNET_ARTIFACTS_SESSION = $bootstrap.session
$env:CIRNET_ARTIFACTS_CONTEXT = $bootstrap.context | ConvertTo-Json -Compress -Depth 10
$env:TMP = $env:TEMP = $env:TMPDIR = $bootstrap.session
$env:PIP_CACHE_DIR = Join-Path $bootstrap.session 'pip-cache'
$env:PYTHONDONTWRITEBYTECODE = '1'
$wheelhouse = Join-Path $bootstrap.session 'wheelhouse'
$dist = Join-Path $bootstrap.session 'dist'
python -B -m pip download --require-hashes --only-binary=:all: -r requirements-verification.lock --dest $wheelhouse
python -B -m pip install --require-hashes --only-binary=:all: --no-index --find-links $wheelhouse -r requirements-verification.lock
python -B scripts/install_contracts.py
$env:SOURCE_DATE_EPOCH = git log -1 --format=%ct
python -B -m build --no-isolation --outdir $dist
$wheel = Join-Path $dist 'cirnet_simulator-0.1.2-py3-none-any.whl'
python -B -m pip install --no-index --no-deps --force-reinstall $wheel
python -B -m pip check
python -B scripts/check_installed.py --wheel $wheel
$tests = Join-Path (Get-Location).Path 'tests'
Push-Location $bootstrap.session
try {
    python -I -B -m pytest $tests --basetemp (Join-Path $bootstrap.session 'pytest')
} finally { Pop-Location }
~~~

The installed check verifies the selected archive SHA256, installed RECORD, dependency identity and source separation. The tests cover model boundaries, unavailable backends, deterministic scheduling, and serialized plans in spawned workers. `-B` is explicit because `-I` ignores `PYTHONDONTWRITEBYTECODE`. Compare the wheel with an independent build from the extracted sdist at the same `SOURCE_DATE_EPOCH` before release.

Store all logs and scratch files under the allocated session from the start. When several repositories participate, provide an explicit owner and every participating Git root in `CIRNET_ARTIFACTS_CONTEXT`. Inspect evidence before guarded cleanup. Preserve selected release artifacts separately.

~~~powershell
node scripts/artifact-paths.mjs --cleanup $env:CIRNET_ARTIFACTS_SESSION
~~~

See the [CI workflow](../../.github/workflows/simulator.yml) and the [dated record](../VERIFICATION.md). These gates verify installed simulation software. Remote owns integrated API and Hardware execution checks.
