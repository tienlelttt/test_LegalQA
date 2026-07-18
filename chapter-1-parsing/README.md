# Chapter 1: Legal Document Parsing & Chunking Module

Đây là Module xử lý văn bản pháp luật thuộc Document Pipeline (Bước 1) trong kiến trúc **LegalQA v2**. 

Module có nhiệm vụ:
- **Cleaning**: Đọc và làm sạch văn bản luật (loại bỏ watermark, header/footer).
- **Parsing**: Bóc tách theo cấu trúc phân cấp pháp lý chuẩn: Chương → Mục → Điều → Khoản → Điểm.
- **Extraction**: Trích xuất siêu dữ liệu (metadata) và các viện dẫn pháp lý phục vụ việc truy vấn có điều kiện.
- **Chunking**: Phân mảnh văn bản bằng chiến lược Adaptive Hierarchical Chunking để không làm mất ngữ cảnh.

> **TÀI LIỆU QUAN TRỌNG:** Để hiểu rõ quyết định kỹ thuật, kiến trúc Production, và phân tích Trade-offs (Tại sao dùng Regex thay vì LLM, tại sao không dùng Langchain Splitter), vui lòng đọc bắt buộc file: **[ENGINEERING_DOCS.md](./ENGINEERING_DOCS.md)** (Tổng quan Tier 1) và các file chi tiết trong thư mục **[adr/](./adr/)** (Chi tiết Tier 2).

---

## 1. Cấu trúc thư mục

```text
chapter-1-parsing/
├── src/
│   ├── exceptions.py       # Định nghĩa lỗi tùy chỉnh
│   ├── ingestor.py         # Mock Layer: Đọc dữ liệu thô
│   ├── cleaner.py          # Xóa rác, bảo vệ pattern pháp luật
│   ├── parser.py           # State Machine Parser dùng Regex
│   ├── extractor.py        # Mock Layer: Trích xuất siêu dữ liệu (Metadata)
│   └── chunker.py          # Adaptive Hierarchical Chunker
├── examples/mock_data.py   # Dữ liệu mẫu (Sample data)
├── benchmark/              # Script đo lường tốc độ, bộ nhớ
├── tests/                  # Unit Test & Integration Test
├── demo.py                 # File chạy Demo E2E Pipeline
├── adr/                    # [TIER 2] Architecture Decision Records
├── ENGINEERING_DOCS.md     # [TIER 1] Tài liệu kiến trúc chuyên sâu
└── README.md               # File hướng dẫn hiện tại
```

*(Lưu ý: Các Schema/Models chuẩn như `Chunk`, `Document` dùng chung cho nhiều module đã nằm ở thư mục `shared/` tại gốc dự án).*

---

## 2. Các lớp mô phỏng (Simulation Layers)

Để dễ dàng phát triển ở môi trường Local (MVP) mà không cần cài đặt hạ tầng hay tốn tiền API, chúng tôi đang sử dụng các Simulation Layer.

Chi tiết về kế hoạch nâng cấp (Migration Guide) sang Production, vui lòng tham chiếu trong thư mục `adr/` (ADR-101, ADR-102, ADR-103).

1. **`MockPyMuPDFIngestor`**: Mô phỏng việc đọc PDF trực tiếp từ file `.txt`.
2. **`MockLLMMetadataExtractor`**: Mô phỏng quá trình gọi LLM để lấy siêu dữ liệu (Title, Status). 

---

## 3. Hướng dẫn sử dụng nhanh (Quickstart)

### Yêu cầu môi trường
Đảm bảo bạn đã cài đặt các thư viện yêu cầu trong môi trường ảo:
```bash
cd chapter-1-parsing
pip install -r requirements.txt
```

### Chạy Demo (End-to-End)
Script `demo.py` đã tự động xử lý lỗi Encoding tiếng Việt trên Windows. Chạy lệnh:
```bash
python demo.py
```
Kết quả mong đợi: Hệ thống in ra màn hình cấu trúc cây (Tree) của các "Điều", "Khoản", "Điểm", kèm danh sách Chunks được sinh ra cùng Context Window liên kết.

### Chạy Tests
Chạy toàn bộ bộ test để đảm bảo State Machine và Regex bắt đúng các luồng logic.
```bash
$env:PYTHONPATH="."  # Cấu hình trên PowerShell Windows
pytest tests/
```
