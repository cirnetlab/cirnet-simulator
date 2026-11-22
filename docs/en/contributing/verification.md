# Build and verify Simulator

[Tiếng Việt](../../vi/contributing/verification.md) · [Documentation](../index.md)

Use CMake 3.21 or newer and a C++20 compiler. This Windows x64 example uses Visual Studio 2022 C++ Build Tools. Write build, test and install outputs into a fresh directory outside all checkouts and Git directories.

~~~powershell
$output = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid())
New-Item -ItemType Directory -Path $output | Out-Null
cmake -S . -B "$output/build" -G 'Visual Studio 17 2022' -A x64
cmake --build "$output/build" --config Release
cmake --install "$output/build" --config Release --prefix "$output/install"
$env:CIRNET_TEST_CPP_WORKER = "$output/install/bin/cirnet-simulator-worker.exe"
& $env:CIRNET_TEST_CPP_WORKER --version
& $env:CIRNET_TEST_CPP_WORKER --protocols
python -m venv "$output/venv"
$python = "$output/venv/Scripts/python.exe"
& $python -m pip install --require-hashes --only-binary=:all: -r requirements-verification.lock
& $python -B -m pytest -q -p no:cacheprovider --basetemp "$output/pytest" tests
Get-FileHash -Algorithm SHA256 -LiteralPath $env:CIRNET_TEST_CPP_WORKER
~~~

Python runs the test harness. The installed worker executes independently. Tests cover digital traces, bounded DC, malformed input, event and capture limits and isolation across requests. Remote verifies the worker artifact for the integrated candidate.
