# Kiểm chứng CIRNET Simulator

[English](../en/verification.md) · Tiếng Việt

[Mục lục tài liệu](index.md)

[Quy trình CI](../../.github/workflows/simulator.yml) của kho chạy trên
Ubuntu khi push lên `master`, mở pull request hoặc chạy thủ công. CI dùng
công cụ DEV và wheel Contracts đã ghim, dựng wheel và sdist Python, xác minh
wheel đã cài, chạy `tests/` từ thư mục ngoài kho và tải cả hai gói lên để rà
soát. Quy trình bật riêng bên dưới dựng và kiểm thử worker native. Bộ kiểm
thử giao thức bỏ qua khi thiếu `CIRNET_TEST_CPP_WORKER`. Cần truyền rõ đường
dẫn bộ kiểm thử bộ điều hợp cho pytest.

## Kiểm chứng wheel Python đã cài

Dùng Node 26 và Python 3.14 để tái lập CI hiện tại. Kích hoạt một môi trường Python mới nằm ngoài mọi bản sao kho mã. Chọn wheel Contracts 0.1.2 đã rà soát và bộ cấp phát DEV đã ghim. Chạy từ kho Simulator trong PowerShell và thay đường dẫn manifest bằng đường dẫn tuyệt đối đã rà soát.

Chạy các lệnh theo thứ tự và dừng khi có lỗi đầu tiên.

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

Bước kiểm tra sau cài đối chiếu SHA256 gói đã chọn, RECORD của bản cài, định danh phụ thuộc và việc cách ly mã nguồn. Kiểm thử bao quát ranh giới mô hình, backend chưa khả dụng, lập lịch tất định và kế hoạch đã tuần tự hóa qua tiến trình con. Dùng rõ `-B` vì `-I` bỏ qua `PYTHONDONTWRITEBYTECODE`. Trước khi phát hành, so sánh wheel với bản dựng độc lập từ sdist đã giải nén tại cùng `SOURCE_DATE_EPOCH`.

## Kiểm chứng worker C++

Dùng phiên đã cấp phát và môi trường Python đã cài ở trên. Chạy các lệnh sau
từ bản sao kho Simulator với CMake từ 3.21 trở lên và Visual Studio 2022
Build Tools. Dừng ở lỗi đầu tiên.

~~~powershell
$session = $env:CIRNET_ARTIFACTS_SESSION
$source = (Get-Location).Path
cmake -S . -B "$session/cpp" -G "Visual Studio 17 2022" -A x64
cmake --build "$session/cpp" --config Release
cmake --install "$session/cpp" --config Release --prefix "$session/cpp-install"
$env:CIRNET_TEST_CPP_WORKER = "$session/cpp-install/bin/cirnet-simulator-worker.exe"
$env:CIRNET_CPP_WORKER = $env:CIRNET_TEST_CPP_WORKER
$env:CIRNET_CPP_WORKER_SHA256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $env:CIRNET_CPP_WORKER).Hash.ToLowerInvariant()
Push-Location $session
try {
    python -I -B -m pytest -q "$source/tests/test_cpp_worker.py" --basetemp "$session/pytest-cpp-worker"
    python -I -B -m pytest -q "$source/tests/native_cpp_backend_cases.py" --basetemp "$session/pytest-cpp-adapter"
} finally { Pop-Location }
~~~

[Bộ kiểm thử giao thức](../../tests/test_cpp_worker.py) kiểm tra frame CNP1
và CNP2, ranh giới mô hình và giới hạn tài nguyên, cùng khả năng tái sử dụng
tiến trình. [Bộ kiểm thử bộ điều hợp](../../tests/native_cpp_backend_cases.py)
kiểm tra định danh worker đã ghim, kết quả và NCAP tương đương với `legacy`,
pool Run và preview riêng, hủy tác vụ và dọn dẹp. Các lệnh lấy mã băm của bản
dựng cục bộ để kiểm thử tại chỗ. Khi kiểm thử worker đã chọn, dùng mã băm đã
rà soát từ manifest ứng viên. Biến cấu hình runtime là `CIRNET_SIM_CPP_WORKER`
và `CIRNET_SIM_CPP_WORKER_SHA256`. [Cấu hình backend](backends.md#worker-c-thử-nghiệm)

## Kiểm tra và dọn phiên

Lưu mọi nhật ký và tệp tạm trong phiên được cấp phát ngay từ đầu. Khi nhiều kho tham gia, chỉ rõ chủ sở hữu và mọi gốc Git tham gia trong `CIRNET_ARTIFACTS_CONTEXT`. Kiểm tra bằng chứng trước khi dọn dẹp có xác minh quyền sở hữu. Giữ riêng các artifact đã chọn để phát hành.

~~~powershell
node scripts/artifact-paths.mjs --cleanup $env:CIRNET_ARTIFACTS_SESSION
~~~

Xem [quy trình CI](../../.github/workflows/simulator.yml) và [hồ sơ theo ngày](../VERIFICATION.md). Các bước này kiểm chứng phần mềm mô phỏng đã cài. Remote phụ trách kiểm tra API và thực thi Hardware tích hợp.
