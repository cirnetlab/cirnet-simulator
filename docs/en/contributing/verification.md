# Build and verify Simulator

[Tiếng Việt](../../vi/contributing/verification.md) · [Documentation](../index.md)

Use CMake 3.21 or newer and a C++20 compiler. This Windows x64 example uses Visual Studio 2022 C++ Build Tools. Write build, test and install outputs into a fresh directory outside all checkouts and Git directories.

Set CIRNET_LOCAL_STORAGE_ROOT and select the reviewed Contracts Node allocator in $allocator. Keep the same session for repeated builds with the same worktree, compiler, generator, architecture and configuration.

~~~powershell
$env:CIRNET_ARTIFACTS_SESSION = node $allocator
if ($LASTEXITCODE) { throw 'Could not allocate a Simulator artifact session.' }
$output = $env:CIRNET_ARTIFACTS_SESSION
cmake -S . -B "$output/build" -G 'Visual Studio 17 2022' -A x64
cmake --build "$output/build" --config Release
cmake --install "$output/build" --config Release --prefix "$output/install"
$env:CIRNET_TEST_CPP_WORKER = "$output/install/bin/cirnet-simulator-worker.exe"
$env:CIRNET_TEST_CPP_WORKER_SHA256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $env:CIRNET_TEST_CPP_WORKER).Hash.ToLowerInvariant()
& $env:CIRNET_TEST_CPP_WORKER --version
& $env:CIRNET_TEST_CPP_WORKER --protocols
python -m venv "$output/venv"
$python = "$output/venv/Scripts/python.exe"
& $python -m pip install --require-hashes --only-binary=:all: -r requirements-verification.lock
& $python -B -m pytest -q -p no:cacheprovider --basetemp "$output/pytest" tests
Get-FileHash -Algorithm SHA256 -LiteralPath $env:CIRNET_TEST_CPP_WORKER
~~~

Python runs the test harness. The installed worker executes independently. The fixtures and expected results in [the worker tests](../../../tests/test_cpp_worker.py) cover digital traces, breadboard net fan-out, exact event budgets with simultaneous input changes, powered quad-gate probe order, bounded DC LED states, malformed input, capture limits and isolation across requests. The powered-device and timing expectations were derived from `migration/python-reference/tests/native_cpp_backend_cases.py` in `cirnet-simulator` revision `7cdee6420a204f9b0cd2120ff9e65ee5ffd52b1c`. The build and tests use this checkout and pinned verification tools. Hardware verifies graph compilation, placement resolution and worker supervision at its integration boundary. Remote verifies the worker artifact for the integrated candidate.
