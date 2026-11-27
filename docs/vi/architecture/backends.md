# Thực thi backend

[English](../../en/architecture/backends.md) · [Tài liệu](../index.md)

Simulator sở hữu kết quả mô phỏng số, DC giới hạn và frame nội bộ CNP1/CNP2. Contracts sở hữu CircuitGraph và NCAP. Hardware xác thực và chuyển đổi kế hoạch, đối chiếu hash tệp thực thi, giám sát worker và mã hóa kết quả. Remote sở hữu việc điều phối và chọn bản phát hành.

[CIRNET Lab-First](https://github.com/cirnetlab/cirnet-rules/blob/master/docs/tai-lieu-kien-tuc-he-thong/cirnet-architecture-lab-first-vi.md) xác định các giai đoạn thực thi và tiêu chí nghiệm thu đích.

`cirnet-simulator-worker --protocols` liệt kê CNP1 và CNP2. Tiến trình được giám sát chạy với `--serve` để xử lý tuần tự qua stdin/stdout. Chế độ một lần đọc một frame rồi đến EOF. Frame bắt đầu bằng trường độ dài 32 bit little-endian và mang tải tin tối đa 16 MiB. Yêu cầu gồm mã giao thức, ID yêu cầu và thế hệ, thời lượng theo nano giây, giới hạn sự kiện và số bản ghi. Phản hồi lặp lại mã giao thức và hai ID.

Worker là một [target CMake dùng C++20](../../../CMakeLists.txt). [Điểm vào của tiến trình](../../../src/worker/worker.cpp) xử lý khung CNP và chuyển việc tính toán cho [bộ mô phỏng sự kiện số](../../../src/worker/worker_digital.cpp) và [bộ giải DC giới hạn](../../../src/worker/worker_dc.hpp). [Giới hạn tiến trình](../../../src/worker/worker_limits.hpp) được áp dụng trước khi xử lý yêu cầu. Chạy [bộ kiểm thử hồi quy worker](../../../tests/test_cpp_worker.py) với tệp thực thi đã cài đặt.

| Giao thức | Đầu vào | Phản hồi thành công |
| --- | --- | --- |
| CNP1 | Cạnh có hướng, cổng lý tưởng, sự kiện đầu vào và đầu dò | Mẫu đầu dò theo thứ tự |
| CNP2 | Bản ghi số với cạnh ánh xạ và cờ bật cổng, cùng nút DC, điện thế, điện trở, nút chặn, bộ lái và LED | Mẫu đầu dò theo thứ tự, mức chân cuối và các cặp trạng thái/dòng điện LED |

Đầu vào số thả nổi giữ giá trị chưa xác định. Ngân sách sự kiện độc lập với ngân sách mẫu. Khi có lỗi, phần capture dở dang bị loại bỏ. CNP2 hỗ trợ các cổng có nguồn và mô hình nguồn/điện trở/LED giới hạn. Hardware sở hữu việc xác thực, hủy và Stop an toàn. [Backend ngspice](ngspice-integration.md) dành trước vẫn ở trạng thái `UNAVAILABLE`.
