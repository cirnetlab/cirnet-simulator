# Kế hoạch tích hợp ngspice

[English](../../en/architecture/ngspice-integration.md) · [Chọn backend](backends.md)

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
