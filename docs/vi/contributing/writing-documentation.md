# Viết và duy trì tài liệu CIRNET Simulator

[English](../../en/contributing/writing-documentation.md) · [Mục lục](../index.md)

Tuân theo [chỉ dẫn của kho](../../../AGENTS.md) và
[quy ước chung của CIRNET](https://github.com/cirnetlab/cirnet-remote/blob/40849a3478b20f31f3882f36852b47a688952516/docs/vi/contributing/writing-documentation.md).
Giữ README gốc bằng tiếng Anh và liên kết đến cả hai mục lục. Dùng cùng
đường dẫn tương đối cho trang tiếng Anh và tiếng Việt hiện hành, rồi cập
nhật chúng cùng nhau. Giữ nguyên lệnh, định danh, phiên bản, giới hạn
và trạng thái khả năng giữa hai ngôn ngữ.

Đặt tài liệu về mô hình Simulator, cách chọn backend và giao thức worker riêng tại đây. Contracts sở hữu schema và catalog. Hardware phụ trách vòng đời trạm và Remote phụ trách điều phối qua REST. Phân biệt cấu hình Python đã phát hành với worker native bật riêng và giữ nguyên hành vi khi mô hình không khả dụng.

Lưu mỗi kế hoạch công việc trong `.superpowers/plans/`. Lưu đặc tả tương
ứng, tiêu chí nghiệm thu và checklist tiến độ trong `.superpowers/specs/`.
Git bỏ qua cả hai đường dẫn trong kho này. Dùng `- [ ]` cho việc đang mở
và chỉ dùng `- [x]` sau khi kiểm chứng. Sau khi kiểm chứng thay đổi, cập
nhật hai trang tương ứng và [nhật ký phát hành](../../changelogs/README.md).

Giữ hồ sơ theo ngày tại đường dẫn hiện có và liệt kê trong cả hai
[mục lục lịch sử](../history/index.md). Dẫn revision Git chính xác cho
kế hoạch hoặc đặc tả đã được thay thế. Lưu nhật ký thô và đầu ra bản dựng
trong phiên ngoài kho do mình sở hữu. Trước khi bàn giao, đối chiếu cặp
ngôn ngữ, kiểm tra liên kết và anchor, rồi rà soát Git diff và đầu ra
Git bỏ qua. [Hướng dẫn kiểm chứng](verification.md)
