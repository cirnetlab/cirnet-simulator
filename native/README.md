# CIRNET Simulator C++ worker

This directory contains the C++20 `cirnet-simulator-worker`, built by the root `CMakeLists.txt`. The worker processes bounded digital and DC requests over the private CNP1/CNP2 protocol on stdin and stdout. The Python adapter in `cirnet_sim/cpp_backend.py` validates and projects graphs, verifies the selected executable, and supervises its processes.

- [Backend configuration and protocol](../docs/en/backends.md#experimental-c-worker) · [Cấu hình backend và giao thức](../docs/vi/backends.md#worker-c-thử-nghiệm)
- [Build and verification](../docs/en/verification.md#verify-the-c-worker) · [Dựng và kiểm chứng](../docs/vi/verification.md#kiểm-chứng-worker-c)
