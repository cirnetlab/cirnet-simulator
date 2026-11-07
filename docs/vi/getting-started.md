# Bắt đầu với CIRNET Simulator

[English](../en/getting-started.md) · Tiếng Việt

[Mục lục tài liệu](index.md)

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

Bộ mô phỏng sự kiện tiếp nhận đồ thị CircuitGraph 1.0, 1.1 và 1.2 được hỗ trợ. Các mô hình tích hợp bao gồm công tắc số, cổng logic, LED và đầu dò, xung nhịp, cùng một tập con DC có giới hạn với HC08 được cấp nguồn, nguồn điện, điện trở và LED. Hình biểu diễn bảng mạch và thiết bị đo không tạo mạng điện. Mô hình chưa nhận diện báo `UNEXECUTABLE`. Thực thi tương tự, SPICE và tín hiệu hỗn hợp vẫn là `UNAVAILABLE`.

Thời gian được tính theo số nguyên nano giây. Độ trễ số mặc định 8 ns là giá trị mô hình phục vụ học tập. Đầu vào thả nổi giữ mức `X`. Bản ghi đo chứa các lần chuyển mức 0/1/X sau khi ổn định, trên tối đa bốn đầu dò được yêu cầu. Giới hạn mặc định là 1 ms, 100.000 sự kiện lập lịch và 100.000 mẫu thu. Giới hạn sự kiện có thể cấu hình tới 1.000.000. Giới hạn mẫu thu được tính riêng. Khi vượt một trong hai giới hạn, lần chạy thất bại và không trả kết quả bị cắt bớt.

Remote phụ trách xem trước qua REST và lưu dữ liệu. Hardware phụ trách nhóm tiến trình, phiên trạm và vô hiệu hóa kết quả khi Stop hoặc reset. Xem [cách chọn backend](backends.md) và [tài liệu miền tín hiệu đã ghim](https://github.com/cirnetlab/cirnet-remote/blob/13a35145b6d15644c7be10d95a5410bf69e11867/docs/vi/architecture/signal-domains-and-simulation.md).
