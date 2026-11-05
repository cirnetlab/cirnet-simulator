# Kiểm chứng wheel Simulator

[English](../en/verification.md) · Tiếng Việt

[Mục lục tài liệu](index.md)

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

Lưu mọi nhật ký và tệp tạm trong phiên được cấp phát ngay từ đầu. Khi nhiều kho tham gia, chỉ rõ chủ sở hữu và mọi gốc Git tham gia trong `CIRNET_ARTIFACTS_CONTEXT`. Kiểm tra bằng chứng trước khi dọn dẹp có xác minh quyền sở hữu. Giữ riêng các artifact đã chọn để phát hành.

~~~powershell
node scripts/artifact-paths.mjs --cleanup $env:CIRNET_ARTIFACTS_SESSION
~~~

Xem [quy trình CI](../../.github/workflows/simulator.yml) và [hồ sơ theo ngày](../VERIFICATION.md). Các bước này kiểm chứng phần mềm mô phỏng đã cài. Remote phụ trách kiểm tra API và thực thi Hardware tích hợp.
