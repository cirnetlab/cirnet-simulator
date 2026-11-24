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
$env:CIRNET_TEST_CPP_WORKER_SHA256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $env:CIRNET_TEST_CPP_WORKER).Hash.ToLowerInvariant()
& $env:CIRNET_TEST_CPP_WORKER --version
& $env:CIRNET_TEST_CPP_WORKER --protocols
python -m venv "$output/venv"
$python = "$output/venv/Scripts/python.exe"
& $python -m pip install --require-hashes --only-binary=:all: -r requirements-verification.lock
& $python -B -m pytest -q -p no:cacheprovider --basetemp "$output/pytest" tests
Get-FileHash -Algorithm SHA256 -LiteralPath $env:CIRNET_TEST_CPP_WORKER
~~~

Python chạy bộ kiểm thử. Worker đã cài thực thi độc lập. Dữ liệu và kết quả mong đợi trong [bộ kiểm thử worker](../../../tests/test_cpp_worker.py) bao quát tín hiệu số, phân nhánh trên mạng breadboard, giới hạn sự kiện chính xác khi đầu vào đổi đồng thời, thứ tự thu tín hiệu của bốn cổng được cấp nguồn, trạng thái LED trong mô hình DC giới hạn, đầu vào sai, giới hạn thu mẫu và tính cô lập giữa các yêu cầu. Kết quả mong đợi về cấp nguồn và thời gian được lấy từ `migration/python-reference/tests/native_cpp_backend_cases.py` trong `cirnet-simulator` tại phiên bản `7cdee6420a204f9b0cd2120ff9e65ee5ffd52b1c`. Quá trình build và kiểm thử dùng checkout này và các công cụ kiểm chứng đã chốt. Hardware kiểm chứng biên dịch đồ thị, phân giải vị trí và giám sát worker tại ranh giới tích hợp. Remote kiểm chứng artifact của worker cho ứng viên hệ thống tích hợp.
