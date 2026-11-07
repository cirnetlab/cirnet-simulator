# Bắt đầu với CIRNET Simulator

[English](../../en/guides/getting-started.md) · Tiếng Việt

[Mục lục tài liệu](../index.md)

Mã nguồn hiện tại dựng `cirnet-simulator==0.1.2` cho Python từ 3.11 trở lên.
Với cấu hình hệ thống CIRNET 0.1.4 đã công bố, cài wheel Simulator và
`cirnet-contracts==0.1.2` trong môi trường mới, dùng đúng mã băm từ
[manifest phát hành](https://github.com/cirnetlab/cirnet-remote/blob/38aea6120920f48cea817827ac2277cce4bef25e/integration/release-set.json). Cấu hình này dùng `legacy`. Tên import chuẩn
là `cirnet_sim`. Bí danh `netcircuit_sim` trỏ tới cùng mô-đun và lớp cho
mã gọi cũ.

Sau khi cài các wheel, chạy kiểm tra này từ ngoài bản sao kho mã. Lệnh in `1`, kết quả của phép AND hai đầu vào.

~~~sh
python -I -B -c "from cirnet_sim import and2; print(and2(1, 1))"
~~~

Xem [phạm vi và giới hạn mô hình](../architecture/backends.md#phạm-vi-và-giới-hạn-mô-hình).

Remote phụ trách xem trước qua REST và lưu dữ liệu. Hardware phụ trách nhóm tiến trình, phiên trạm và vô hiệu hóa kết quả khi Stop hoặc reset. Xem [cách chọn backend](../architecture/backends.md) và [tài liệu miền tín hiệu đã ghim](https://github.com/cirnetlab/cirnet-remote/blob/13a35145b6d15644c7be10d95a5410bf69e11867/docs/vi/architecture/signal-domains-and-simulation.md).
