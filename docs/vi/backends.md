# Chọn backend và thực thi

[English](../en/backends.md) · Tiếng Việt

[Mục lục tài liệu](index.md)

`CIRNET_SIMULATION_BACKEND` chọn bộ điều hợp tích hợp khi tạo ứng dụng hoặc trạm. Mặc định là `legacy`, hỗ trợ các mô hình số và tập con DC hiện có. `ngspice` được dành cho tích hợp sau và báo `UNAVAILABLE`. Backend này không tạo mẫu và không khởi chạy chương trình gốc. Thiết lập chuẩn được ưu tiên hơn `NETCIRCUIT_SIMULATION_BACKEND`. Thuộc tính đồ thị không thể chọn bộ điều hợp.

Mã ứng dụng xác định ID một lần bằng `cirnet_sim.backends.select_backend_id()`. Truyền ID vào `compile_graph(graph, backend_id=...)` và `preview_physical_graph(graph, backend_id=...)`. Kiểm tra trạng thái khả dụng trước khi thực thi. Kế hoạch đã biên dịch mang ID backend, phiên bản bộ điều hợp và định dạng kế hoạch. Hàm `run_plan(plan, configuration, vectors, clock_config, inputs)` của tiến trình thực thi tra theo định danh cố định này. Nếu thiếu hoặc sai nhà cung cấp, thao tác thất bại. Hardware dùng ánh xạ chỉ đọc `.directions` để xét cho phép chạy.

Mã ứng dụng tin cậy có thể cung cấp `BackendRegistry` với danh sách nhà cung cấp tường minh. Mỗi nhà cung cấp công bố `BackendDescriptor` bất biến và triển khai biên dịch, thực thi, xem trước. Biên dịch phải trả dữ liệu có thể tuần tự hóa, bao gồm thiết lập thực thi và hướng các điểm cuối. Mỗi tiến trình con cần registry tương đương của riêng nó. Hardware hiện dùng các nhà cung cấp tích hợp. Simulator không tự tìm nhà cung cấp từ đường dẫn mô-đun hoặc nội dung đồ thị. Xem [mã nguồn backend](../../cirnet_sim/backends.py).

Để khôi phục trong bản phát hành này, chọn `legacy`. Khi khôi phục bộ artifact cũ, khôi phục cùng lúc Simulator, Contracts và phiên bản được ghim ở bên tiêu thụ. Đối chiếu artifact cũ bằng SHA256, kể cả khi số phiên bản trùng nhau. Không cần ghi lại đồ thị hoặc bản ghi đo đã lưu.
