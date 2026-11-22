# Build và kiểm chứng Simulator

[English](../../en/contributing/verification.md) · [Tài liệu](../index.md)

Dùng CMake 3.21 trở lên và trình biên dịch C++20. Ví dụ Windows x64 dùng Visual Studio 2022 C++ Build Tools. Ghi đầu ra build, kiểm thử và cài đặt vào thư mục mới bên ngoài mọi checkout và thư mục Git.

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

Python chạy bộ kiểm thử. Worker đã cài thực thi độc lập. Bộ kiểm thử bao quát tín hiệu số, DC giới hạn, đầu vào sai, giới hạn sự kiện và thu mẫu, cùng tính cô lập giữa các yêu cầu. Remote kiểm chứng artifact của worker cho ứng viên hệ thống tích hợp.
