# Chọn backend và thực thi

[English](../en/backends.md) · Tiếng Việt

[Mục lục tài liệu](index.md)

`CIRNET_SIMULATION_BACKEND` chọn bộ điều hợp tích hợp khi tạo ứng dụng hoặc trạm. Mặc định là `legacy`, hỗ trợ các mô hình số và tập con DC hiện có. `ngspice` được dành cho tích hợp sau và báo `UNAVAILABLE`. Backend này không tạo mẫu và không khởi chạy chương trình gốc. Thiết lập chuẩn được ưu tiên hơn `NETCIRCUIT_SIMULATION_BACKEND`. Thuộc tính đồ thị không thể chọn bộ điều hợp.

Mã ứng dụng xác định ID một lần bằng `cirnet_sim.backends.select_backend_id()`. Truyền ID vào `compile_graph(graph, backend_id=...)` và `preview_physical_graph(graph, backend_id=...)`. Kiểm tra trạng thái khả dụng trước khi thực thi. Kế hoạch đã biên dịch mang ID backend, phiên bản bộ điều hợp và định dạng kế hoạch. Hàm `run_plan(plan, configuration, vectors, clock_config, inputs)` của tiến trình thực thi tra theo định danh cố định này. Nếu thiếu hoặc sai nhà cung cấp, thao tác thất bại. Hardware dùng ánh xạ chỉ đọc `.directions` để xét cho phép chạy.

Mã ứng dụng tin cậy có thể cung cấp `BackendRegistry` với danh sách nhà cung cấp tường minh. Mỗi nhà cung cấp công bố `BackendDescriptor` bất biến và triển khai biên dịch, thực thi, xem trước. Biên dịch phải trả dữ liệu có thể tuần tự hóa, bao gồm thiết lập thực thi và hướng các điểm cuối. Mỗi tiến trình con cần registry tương đương của riêng nó. Hardware hiện dùng các nhà cung cấp tích hợp. Simulator không tự tìm nhà cung cấp từ đường dẫn mô-đun hoặc nội dung đồ thị. Xem [mã nguồn backend](../../cirnet_sim/backends.py).

Để khôi phục trong bản phát hành này, chọn `legacy`. Khi khôi phục bộ artifact cũ, khôi phục cùng lúc Simulator, Contracts và phiên bản được ghim ở bên tiêu thụ. Đối chiếu artifact cũ bằng SHA256, kể cả khi số phiên bản trùng nhau. Không cần ghi lại đồ thị hoặc bản ghi đo đã lưu.

## Worker C++ thử nghiệm

Để chọn adapter này ở Remote và Hardware, đặt `CIRNET_SIMULATION_BACKEND=cpp`, `CIRNET_SIM_CPP_WORKER` là đường dẫn tuyệt đối đến worker và `CIRNET_SIM_CPP_WORKER_SHA256` là digest của artifact đã chọn. Host kiểm tra worker trước khi khởi chạy. Backend `cpp` báo không khả dụng nếu thiếu hoặc sai thông tin ghim. Mã tích hợp cũng có thể đưa `CppBackend` từ `cirnet_sim.cpp_backend` vào một `BackendRegistry` tường minh.

Run và preview dùng hai pool riêng. Pool Run lấy số slot từ `CIRNET_SIMULATION_WORKERS`, mặc định bốn tác vụ, với deadline IPC 10 giây. Pool preview nhận một tác vụ với deadline IPC hai giây. Host từ chối yêu cầu ngay khi hết slot. Mỗi slot tái sử dụng một tiến trình riêng. Host thu hồi tiến trình khi hết hạn, hủy tác vụ, worker thoát hoặc trả phản hồi sai. Hardware chờ tác vụ Run đã hủy dọn dẹp xong rồi mới xác nhận Stop hoặc reset an toàn. Để chuyển về `legacy`, dừng công việc đang chạy và khởi động lại các dịch vụ với cấu hình tương ứng.

### Giao thức riêng của worker

Lệnh `cirnet-simulator-worker --serve` xử lý từng yêu cầu một qua stdin/stdout. Chế độ chạy một lần nhận một frame rồi đến EOF. Mỗi frame gồm số byte 32 bit little-endian và payload tối đa 16 MiB. Đầu yêu cầu chứa tag giao thức bốn byte, ID yêu cầu và generation 64 bit, thời lượng tính theo nano giây và sáu trường 32 bit cho giới hạn sự kiện và số bản ghi. Phản hồi trả lại tag và cả hai ID. Adapter kiểm tra các trường này trước khi chấp nhận kết quả.

| Tag | Nội dung yêu cầu sau header chung | Kết quả thành công sau header chung |
| --- | --- | --- |
| `CNP1` | Cạnh có hướng, cổng lý tưởng, sự kiện đầu vào và probe | Các mẫu đo theo thứ tự |
| `CNP2` | Sáu số đếm DC, cạnh ánh xạ mức đầu vào, cổng có cờ cấp nguồn, sự kiện, probe, điện thế nguồn, điện trở, nút bị chặn, ngõ ra cấp dòng và LED | Các mẫu đo theo thứ tự, mức chân cuối cùng và cặp trạng thái/dòng điện cho mỗi LED |

Vòng lặp sự kiện số dùng ba mức 0, 1 và chưa biết. Preview đặt độ trễ cổng bằng 0 và giữ clock ở mức ban đầu. CNP2 hỗ trợ mô hình DC nối tiếp giới hạn và cổng có cấp nguồn. Adapter Python chuyển tiếp xác thực, chuyển đổi đồ thị và định dạng kết quả. Contracts mã hóa payload NCAP công khai tại Hardware.

Worker kiểm tra giới hạn sự kiện và mẫu đo, đồng thời áp giới hạn bộ nhớ 256 MiB cho mỗi tiến trình ở cấp hệ điều hành. Profile phát hành mặc định chọn `legacy`.

Build và cài chương trình C++20 trong thư mục ngoài Git do allocator cấp. Các lệnh sau dùng Visual Studio 2022 Build Tools trên Windows.

```powershell
cmake -S . -B "$env:CIRNET_ARTIFACTS_SESSION/cpp" -G "Visual Studio 17 2022" -A x64
cmake --build "$env:CIRNET_ARTIFACTS_SESSION/cpp" --config Release
cmake --install "$env:CIRNET_ARTIFACTS_SESSION/cpp" --config Release --prefix "$env:CIRNET_ARTIFACTS_SESSION/cpp-install"
$env:CIRNET_TEST_CPP_WORKER = "$env:CIRNET_ARTIFACTS_SESSION/cpp-install/bin/cirnet-simulator-worker.exe"
python -B -m pytest -q tests/test_cpp_worker.py --basetemp "$env:CIRNET_ARTIFACTS_SESSION/pytest-cpp-worker"
```

## Kế hoạch tích hợp ngspice

Dùng mã nguồn ngspice upstream cho backend analog và hỗn hợp bật riêng theo
cấu hình. Ứng viên giai đoạn 1 dùng worker C++ của CIRNET cho các mô hình số và DC giới
hạn hiện có. Thử nghiệm tái lập đầu tiên dự kiến dùng tag upstream
`ngspice-46` và gói mã nguồn `ngspice-46.tar.gz`. Gói tải từ upstream
khớp SHA-256 trong công thức Homebrew đã ghim
`a0d1699af1940b06649276dcd6ff5a566c8c0cad01b2f7b5e99dedbb4d64c19b`.
Hash mã nguồn và đầu vào mô hình đã được **XÁC MINH**. Build binary, băm
gói mô hình và rà soát đúng bộ tệp phân phối ở trạng thái **NOT RUN**.
[Gói mã nguồn upstream](https://sourceforge.net/projects/ngspice/files/ng-spice-rework/old-releases/46/ngspice-46.tar.gz/download) ·
[Danh mục bản phát hành upstream](https://sourceforge.net/projects/ngspice/files/ng-spice-rework/old-releases/46/) ·
[Công thức Homebrew đã ghim](https://github.com/Homebrew/homebrew-core/blob/539f6abfdfdff8af39757bc100dfbce1db0c5618/Formula/lib/libngspice.rb#L3-L5)

Mạch RC đầu tiên dùng điện trở, tụ điện và nguồn áp tích hợp của ngspice.
Ghim đầu vào mô hình XSPICE từ `src/xspice/icm/digital/` trong gói nguồn.
Mỗi hash tính theo thứ tự `cfunc.mod`, một byte NUL và `ifspec.ifs`.
Thư viện code model sau khi build cần hash riêng.

| Đầu vào mô hình | SHA-256 |
| --- | --- |
| `d_and` | `f77686eed70f915eb3ce10030435b5462285ff7d1659e59f660698e77bea1097` |
| `adc_bridge` | `0b9d31f3de5d4ea3e458a1d7e1d2e1681fbe4a68d1609684458a87fd66115229` |
| `dac_bridge` | `900462caf6e1826eeb25f81c09f0e16a3c7fcc5d3238711561d46c95060d68d8` |

1. **Build và xác minh đầu vào.** Ghi revision, digest gói mã nguồn, bản vá,
   nền tảng đích, trình biên dịch và tùy chọn build. Build thử thư viện
   dùng chung với configure và `--with-ngshared --enable-xspice --disable-debug`.
   Ghim SHA-256 của từng binary hoặc thư viện dùng chung
   và từng thư viện code model hoặc gói mô hình. Ghi mã định danh SPDX hoặc
   tham chiếu giấy phép theo từng thành phần, kèm văn bản giấy phép và thông
   báo bản quyền của đúng các tệp phân phối. `COPYING` của bản phát hành
   dùng BSD sửa đổi cho phần lớn mã nguồn và nêu các ngoại lệ, gồm mô
   hình bảng của XSPICE. Rà soát mọi thành phần có trong bản build đã chọn.
   [Hướng dẫn ngspice](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf) ·
   [COPYING của upstream](https://sourceforge.net/p/ngspice/ngspice/ci/master/tree/COPYING)
2. **Chọn ranh giới cách ly.** Bắt đầu với tiến trình con ngspice không giao
   diện đồ họa đã ghim, có kiểm soát đầu vào và đầu ra, giới hạn tài nguyên và
   deadline từ host. Đánh giá thư viện C dùng chung trong worker riêng khi
   cần callback cho netlist trong bộ nhớ, dữ liệu bộ giải hoặc sự kiện
   XSPICE. API cung cấp `ngSpice_Circ`, callback dữ liệu và sự kiện, cùng
   `ngSpice_Init_Sync` để cấp nguồn từ host và đồng bộ bước mô phỏng quá độ.
   Khi nhúng trực tiếp, thư viện dùng chung tiến trình với bên gọi. Giữ ranh
   giới tiến trình cho cả hai cách tích hợp. Kiểm tra Stop qua giao diện bộ
   giải, buộc dừng và thu hồi tiến trình khi quá hạn, reset và loại kết quả
   trả muộn.
   Lệnh `bg_halt` có thể cần thời gian mới có hiệu lực.
   [Giao diện thư viện dùng chung](https://ngspice.sourceforge.io/shared.html) ·
   [Hướng dẫn ngspice](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf)
3. **Sinh netlist từ đồ thị đã xác thực.** Chỉ dùng ánh xạ linh kiện và mô
   hình đã duyệt trong catalog có phiên bản, tham số có giới hạn và đơn vị
   rõ ràng, tên nút do adapter sinh và tham chiếu điện tường minh. Adapter
   quyết định chỉ thị của bộ mô phỏng và đường dẫn mô hình. Từ chối netlist,
   lệnh điều khiển, chỉ thị include và đường dẫn thư viện do người dùng cung
   cấp. Giới hạn thời gian giải, kích thước kết quả và số kênh trước khi chạy.
4. **Đối chiếu mô phỏng và capture.** Kiểm tra điểm làm việc DC, quá độ RC,
   cổng số lý tưởng và clock, cùng mạch analog/số có cầu A/D và D/A tường
   minh. So thứ tự sự kiện số, thay đổi đồng thời, timestamp nguyên theo
   nano giây, độ trễ và 0/1/X với bản C++ ở các mô hình tương ứng. Ghi cách
   ánh xạ trạng thái logic và độ mạnh ngõ ra của XSPICE, gồm trường
   hợp chưa biết và trở kháng cao. Giữ tương thích NCAP v1 cho tín hiệu số.
   Với capture analog, giữ trục thời gian của bộ giải và quy định cách lấy
   mẫu trước khi dùng định dạng có tần số cố định. Ghi đơn vị, nguồn gốc mô
   phỏng, định danh mô hình và kết quả thiếu hoặc không hợp lệ.
   [Tổng quan XSPICE](https://ngspice.sourceforge.io/xspiceusage.html) ·
   [Hướng dẫn ngspice](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf)
5. **Chỉ công bố khả năng đã kiểm thử.** Kiểm tra việc chọn lại đúng
   artifact, mô hình được hỗ trợ, tương thích capture, lỗi không hội tụ,
   timeout, worker bị lỗi và cách quay về backend hiện có. Chỉ bật khả năng
   trên đúng nền tảng, worker và gói mô hình đã xác minh. Cho tới khi đạt
   gate này, `ngspice` báo `UNAVAILABLE`.
