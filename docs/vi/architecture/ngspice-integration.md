# Đầu vào nghiên cứu ngspice

[English](../../en/architecture/ngspice-integration.md) · [Chọn backend](backends.md)

Bộ chọn analog và tín hiệu hỗn hợp `ngspice` vẫn báo `UNAVAILABLE`.
Ứng viên giai đoạn 1 dùng worker C++ của CIRNET cho mô hình số và DC giới
hạn. Nghiên cứu đã kiểm tra tag upstream
`ngspice-46` và gói mã nguồn `ngspice-46.tar.gz`. Gói tải từ upstream
khớp SHA-256 trong công thức Homebrew đã ghim
`a0d1699af1940b06649276dcd6ff5a566c8c0cad01b2f7b5e99dedbb4d64c19b`.
Hash mã nguồn và đầu vào mô hình đã được **XÁC MINH**. Build binary, băm
gói mô hình và rà soát đúng bộ tệp phân phối ở trạng thái **NOT RUN**.
[Gói mã nguồn upstream](https://sourceforge.net/projects/ngspice/files/ng-spice-rework/old-releases/46/ngspice-46.tar.gz/download) ·
[Danh mục bản phát hành upstream](https://sourceforge.net/projects/ngspice/files/ng-spice-rework/old-releases/46/) ·
[Công thức Homebrew đã ghim](https://github.com/Homebrew/homebrew-core/blob/539f6abfdfdff8af39757bc100dfbce1db0c5618/Formula/lib/libngspice.rb#L3-L5)

Đầu vào mô hình XSPICE đã xác minh nằm trong `src/xspice/icm/digital/`
của gói nguồn.
Mỗi hash tính theo thứ tự `cfunc.mod`, một byte NUL và `ifspec.ifs`.
Thư viện code model sau khi build cần hash riêng.

| Đầu vào mô hình | SHA-256 |
| --- | --- |
| `d_and` | `f77686eed70f915eb3ce10030435b5462285ff7d1659e59f660698e77bea1097` |
| `adc_bridge` | `0b9d31f3de5d4ea3e458a1d7e1d2e1681fbe4a68d1609684458a87fd66115229` |
| `dac_bridge` | `900462caf6e1826eeb25f81c09f0e16a3c7fcc5d3238711561d46c95060d68d8` |

## Tham chiếu

[Hướng dẫn ngspice](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf) ·
[COPYING của upstream](https://sourceforge.net/p/ngspice/ngspice/ci/master/tree/COPYING) ·
[Giao diện thư viện dùng chung](https://ngspice.sourceforge.io/shared.html) ·
[Tổng quan XSPICE](https://ngspice.sourceforge.io/xspiceusage.html) ·
[Đề xuất tích hợp gốc](https://github.com/cirnetlab/cirnet-simulator/blob/0831ec64459a4880da9d361dae084f1bf857d853/docs/vi/architecture/ngspice-integration.md)
