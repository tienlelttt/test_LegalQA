# Chapter 2: Vector Database & Embedding

Module này thuộc Phase **Document Pipeline**, chịu trách nhiệm biến đổi các đoạn văn bản (Chunks) từ Module 1 thành các Vector ngữ nghĩa, sau đó lưu trữ vào hệ thống Vector Database.

> **TÀI LIỆU QUAN TRỌNG:** Để hiểu sâu về thuật toán, phân tích kiến trúc, lý do vì sao chọn Qdrant thay vì Milvus, và lộ trình nâng cấp (Production Migration), vui lòng đọc bắt buộc file: **[ENGINEERING_DOCS.md](./ENGINEERING_DOCS.md)** (Tổng quan Tier 1) và các file chi tiết trong thư mục **[adr/](./adr/)** (Chi tiết Tier 2).

---

## 1. Cấu trúc thư mục

```text
chapter-2-vector-db/
├── module2/
│   ├── embedder.py           # Mã hóa Dense Vector
│   ├── qdrant_store.py       # Tương tác với Qdrant Vector DB
│   ├── sparse_indexer.py     # Simulation Layer: BM25 Sparse Indexer
│   ├── graph_store.py        # Simulation Layer: Memory Graph (Neo4j Mock)
│   ├── retriever.py          # Giao diện Tìm kiếm: Dense, Sparse, Graph, Hybrid
│   └── index_pipeline.py     # Pipeline hợp nhất: Chunk -> Dense -> Sparse -> Graph
├── tests/                    # Unit tests & Integration tests
├── demo_indexing.py          # Script chạy toàn bộ E2E Ingestion Pipeline
├── requirements.txt          # Danh sách thư viện bắt buộc
├── adr/                      # [TIER 2] Architecture Decision Records
├── ENGINEERING_DOCS.md       # [TIER 1] Tài liệu kiến trúc chuyên sâu
└── README.md                 # (File này) Hướng dẫn nhanh
```

*(Lưu ý: Mọi dữ liệu cấu hình và models dùng chung (như schema `Chunk`) đã được chuyển ra thư mục `shared/` ở Root dự án).*

---

## 2. Các lớp mô phỏng (Simulation Layers)

Để chạy được Hybrid Retrieval trong giai đoạn Local/MVP mà không bị kẹt ở khâu cấu hình hạ tầng phức tạp, chúng tôi sử dụng các lớp mô phỏng (Simulation Layers). 

Chi tiết về kế hoạch nâng cấp (Migration Guide) sang Production cho từng Simulation Layer, vui lòng tham chiếu trong thư mục `adr/` (ADR-201, ADR-202, ADR-203, ADR-204).

1. **`BM25SparseIndexer`**: Giả lập tìm kiếm theo từ khóa (Exact Match) chạy trên RAM thay cho Qdrant Sparse/Elasticsearch.
2. **`MemoryGraphRepository`**: Giả lập lưu trữ Knowledge Graph trên RAM thay cho Neo4j.

---

## 3. Hướng dẫn cài đặt

Di chuyển vào thư mục dự án và kích hoạt môi trường ảo (nếu có), sau đó cài đặt thư viện:

```bash
cd chapter-2-vector-db
pip install -r requirements.txt
```

Các thư viện chính bao gồm:
- `sentence-transformers`: Nhúng văn bản (Embedding) bằng HuggingFace models.
- `qdrant-client`: SDK giao tiếp với Qdrant Vector Database.
- `rank_bm25`: Hỗ trợ thuật toán BM25 cho Sparse Index Simulation.

---

## 4. Hướng dẫn chạy Demo (Quickstart)

File `demo_indexing.py` minh họa vòng lặp (End-to-End) xử lý dữ liệu: 
`Đọc dữ liệu Text -> Parse (Module 1) -> Chunk (Module 1) -> Embed (Module 2) -> Lưu vào Qdrant (Module 2) -> Tìm kiếm (Module 2)`.

```bash
# Bật ép kiểu UTF-8 (rất quan trọng trên Windows)
$env:PYTHONIOENCODING="utf-8"

# Chạy Demo
python demo_indexing.py
```

Kết quả mong đợi: Hệ thống tải model, hiển thị tiến độ Embedding, thông báo insert thành công vào Qdrant In-memory, và trả về top kết quả liên quan cho các câu hỏi truy vấn mẫu thông qua Hybrid Search.

---

## 5. Chạy Unit Test

Đảm bảo bạn đứng ở thư mục Root dự án (`d:\test`), do các module có thể import lẫn nhau và chia sẻ Schema.

```bash
$env:PYTHONPATH="."
pytest chapter-2-vector-db/tests/
```
