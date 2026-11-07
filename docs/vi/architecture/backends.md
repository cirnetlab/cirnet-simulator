# Chọn backend và thực thi

[English](../../en/architecture/backends.md) · Tiếng Việt

[Mục lục tài liệu](../index.md)

`CIRNET_SIMULATION_BACKEND` chọn bộ điều hợp tích hợp khi tạo ứng dụng
hoặc trạm. Thiết lập này được ưu tiên hơn `NETCIRCUIT_SIMULATION_BACKEND`.
Thuộc tính đồ thị không thể chọn bộ điều hợp.

| Giá trị | Khả dụng |
| --- | --- |
| `legacy` | Mặc định. Hỗ trợ mô hình số tất định và tập con DC giới hạn. |
| `cpp` | Bật riêng trong mã nguồn hiện tại. Cần worker C++ được chọn riêng và mã SHA-256 của worker. |
| `ngspice` | Dành cho tương lai và báo `UNAVAILABLE`. Báo không có kênh và không tạo mẫu. |

[Cấu hình CIRNET 0.1.4 đã công bố](https://github.com/cirnetlab/cirnet-remote/blob/38aea6120920f48cea817827ac2277cce4bef25e/integration/release-set.json) chọn `legacy`. Tổ hợp r7
giai đoạn 1 riêng đã đạt Gate 1 trên Windows x64 với `cpp`. SPICE và HIL
vật lý vẫn ở trạng thái `NOT RUN` với ứng viên đó.
[Kết quả Gate 1](https://github.com/cirnetlab/cirnet-remote/blob/13a35145b6d15644c7be10d95a5410bf69e11867/docs/vi/architecture/native-migration.md#quyết-định-gate-1-trên-windows-x64)

Mã ứng dụng xác định ID một lần bằng `cirnet_sim.backends.select_backend_id()`. Truyền ID vào `compile_graph(graph, backend_id=...)` và `preview_physical_graph(graph, backend_id=...)`. Kiểm tra trạng thái khả dụng trước khi thực thi. Kế hoạch đã biên dịch mang ID backend, phiên bản bộ điều hợp và định dạng kế hoạch. Hàm `run_plan(plan, configuration, vectors, clock_config, inputs)` của tiến trình thực thi tra theo định danh cố định này. Nếu thiếu hoặc sai nhà cung cấp, thao tác thất bại. Hardware dùng ánh xạ chỉ đọc `.directions` để xét cho phép chạy.

Mã ứng dụng tin cậy có thể cung cấp `BackendRegistry` với danh sách nhà cung cấp tường minh. Mỗi nhà cung cấp công bố `BackendDescriptor` bất biến và triển khai biên dịch, thực thi, xem trước. Biên dịch phải trả dữ liệu có thể tuần tự hóa, bao gồm thiết lập thực thi và hướng các điểm cuối. Mỗi tiến trình con cần registry tương đương của riêng nó. Hardware hiện dùng các nhà cung cấp tích hợp. Simulator không tự tìm nhà cung cấp từ đường dẫn mô-đun hoặc nội dung đồ thị. Xem [mã nguồn backend](../../../cirnet_sim/backends.py).

Để khôi phục trong bản phát hành này, chọn `legacy`. Khi khôi phục bộ artifact cũ, khôi phục cùng lúc Simulator, Contracts và phiên bản được ghim ở bên tiêu thụ. Đối chiếu artifact cũ bằng SHA256, kể cả khi số phiên bản trùng nhau. Không cần ghi lại đồ thị hoặc bản ghi đo đã lưu.

## Worker C++ thử nghiệm

Để chọn bộ điều hợp này ở Remote và Hardware, đặt
`CIRNET_SIMULATION_BACKEND=cpp`, `CIRNET_SIM_CPP_WORKER` thành đường dẫn
tuyệt đối tới binary và `CIRNET_SIM_CPP_WORKER_SHA256` thành mã băm của
artifact đã chọn. Cần cả hai giá trị ghim để đăng ký backend. Giá trị sai
định dạng làm cấu hình thất bại. Tệp không đọc được hoặc sai mã băm làm worker
khởi chạy thất bại. Mã ứng dụng tin cậy cũng có thể thêm `CppBackend` từ
`cirnet_sim.cpp_backend` vào `BackendRegistry` tường minh.

Run và preview dùng hai pool riêng. Pool Run lấy số slot từ `CIRNET_SIMULATION_WORKERS`, mặc định bốn tác vụ, với deadline IPC 10 giây. Pool preview nhận một tác vụ với deadline IPC hai giây. Host từ chối yêu cầu ngay khi hết slot. Mỗi slot tái sử dụng một tiến trình riêng. Host thu hồi tiến trình khi hết hạn, hủy tác vụ, worker thoát hoặc trả phản hồi sai. Hardware chờ tác vụ Run đã hủy dọn dẹp xong rồi mới xác nhận Stop hoặc reset an toàn. Để chuyển về `legacy`, dừng công việc đang chạy và khởi động lại các dịch vụ với cấu hình tương ứng.

### Giao thức riêng của worker

Lệnh `cirnet-simulator-worker --serve` xử lý từng yêu cầu một qua stdin/stdout. Chế độ chạy một lần nhận một frame rồi đến EOF. Mỗi frame gồm số byte 32 bit little-endian và payload tối đa 16 MiB. Đầu yêu cầu chứa tag giao thức bốn byte, ID yêu cầu và generation 64 bit, thời lượng tính theo nano giây và sáu trường 32 bit cho giới hạn sự kiện và số bản ghi. Phản hồi trả lại tag và cả hai ID. Adapter kiểm tra các trường này trước khi chấp nhận kết quả.

| Tag | Nội dung yêu cầu sau header chung | Kết quả thành công sau header chung |
| --- | --- | --- |
| `CNP1` | Cạnh có hướng, cổng lý tưởng, sự kiện đầu vào và probe | Các mẫu đo theo thứ tự |
| `CNP2` | Sáu số đếm DC, cạnh ánh xạ mức đầu vào, cổng có cờ cấp nguồn, sự kiện, probe, điện thế nguồn, điện trở, nút bị chặn, ngõ ra cấp dòng và LED | Các mẫu đo theo thứ tự, mức chân cuối cùng và cặp trạng thái/dòng điện cho mỗi LED |

Vòng lặp sự kiện số dùng ba mức 0, 1 và chưa biết. Preview đặt độ trễ cổng bằng 0 và giữ clock ở mức ban đầu. CNP2 hỗ trợ mô hình DC nối tiếp giới hạn và cổng có cấp nguồn. Adapter Python chuyển tiếp xác thực, chuyển đổi đồ thị và định dạng kết quả. Contracts mã hóa payload NCAP công khai tại Hardware.

Worker kiểm tra giới hạn sự kiện và mẫu đo, đồng thời áp giới hạn bộ nhớ 256 MiB cho mỗi tiến trình ở cấp hệ điều hành.

Xem [cách dựng và kiểm chứng worker C++](../contributing/verification.md#kiểm-chứng-worker-c).

## Phạm vi và giới hạn mô hình

Bộ mô phỏng sự kiện tiếp nhận đồ thị CircuitGraph 1.0, 1.1 và 1.2 được hỗ trợ. Các mô hình tích hợp bao gồm công tắc số, cổng logic, LED và đầu dò, xung nhịp, cùng một tập con DC có giới hạn với HC08 được cấp nguồn, nguồn điện, điện trở và LED. Hình biểu diễn bảng mạch và thiết bị đo không tạo mạng điện. Mô hình chưa nhận diện báo `UNEXECUTABLE`. Thực thi tương tự, SPICE và tín hiệu hỗn hợp vẫn là `UNAVAILABLE`.

Thời gian được tính theo số nguyên nano giây. Độ trễ số mặc định 8 ns là giá trị mô hình phục vụ học tập. Đầu vào thả nổi giữ mức `X`. Bản ghi đo chứa các lần chuyển mức 0/1/X sau khi ổn định, trên tối đa bốn đầu dò được yêu cầu. Giới hạn mặc định là 1 ms, 100.000 sự kiện lập lịch và 100.000 mẫu thu. Giới hạn sự kiện có thể cấu hình tới 1.000.000. Giới hạn mẫu thu được tính riêng. Khi vượt một trong hai giới hạn, lần chạy thất bại và không trả kết quả bị cắt bớt.

## Kế hoạch tích hợp ngspice

Backend tương tự và tín hiệu hỗn hợp vẫn báo `UNAVAILABLE`. [Đề xuất tích hợp ngspice](ngspice-integration.md)
ghi các đầu vào đã xác minh, ranh giới tiến trình dự kiến và tiêu chí nghiệm thu.
