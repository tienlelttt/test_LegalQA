# ADR 203: Chiến lược Hybrid Search (Dense + Sparse BM25 + Reciprocal Rank Fusion)

## 1. Context
Văn bản luật chứa các thực thể bắt buộc phải "khớp chính xác" (Exact Match), như "Điều 15", "Nghị định 45/2023/NĐ-CP". Dense Embedding (Vector) thường học được ngữ nghĩa (ví dụ: "chó" gần với "mèo") nhưng lại hay thất bại khi tìm Exact Match (ví dụ: "Điều 15" có thể bị nhầm với "Điều 16" vì số 15 và 16 có vector na ná nhau).

## 2. Problem Statement
**Làm sao để kết hợp sức mạnh thấu hiểu ngữ nghĩa của Dense Retrieval và khả năng bắt từ khóa chính xác của Sparse Retrieval?**

## 3. Alternatives Considered

**Option A: Chỉ dùng Dense (Vector)**
- **Ưu điểm**: Dễ triển khai, tiết kiệm RAM.
- **Nhược điểm**: Bỏ sót hoàn toàn các truy vấn tìm đích danh số hiệu luật hoặc tên riêng cụ thể.

**Option B: Dense + Keyword Filter (Lọc Metadata)**
- **Ưu điểm**: Nhanh, chính xác nếu Keyword map đúng.
- **Nhược điểm**: Filter là loại trừ cứng (Hard filter). Nếu user gõ sai một ký tự (vd "Nghị đing"), kết quả = 0.

**Option C: Hybrid Search (Dense + Sparse/BM25) kết hợp Reciprocal Rank Fusion (RRF)**
- **Ưu điểm**: Khắc phục triệt để yếu điểm của cả 2 phương pháp. BM25 tìm từ khóa mềm dẻo, Dense tìm ngữ nghĩa. Thuật toán RRF ghép 2 danh sách kết quả lại cực kỳ mượt mà không cần phải tinh chỉnh trọng số (Alpha) thủ công.
- **Nhược điểm**: Code phức tạp hơn, tốn RAM/Disk để lưu 2 loại Index (Dense + Inverted Index).

## 4. Decision
Quyết định: **Chọn Option C (Hybrid Search với RRF)**.
- **Kiến trúc**: Khi Query đến, hệ thống bắn song song 2 luồng: `DenseRetriever` gọi Qdrant, `SparseRetriever` gọi BM25 Index. Sau đó gộp bằng RRF, lấy top K chunk cao điểm nhất.

## 5. Trade-offs (8 Trục)
- **Performance**: Nhanh, nhưng cần xử lý đa luồng (Async/Thread) để 2 query chạy đồng thời, che giấu độ trễ.
- **Memory**: Tốn thêm RAM/Disk đáng kể để lưu Inverted Index (tần suất từ vựng) cho BM25.
- **Latency**: Tăng khoảng 10-20ms cho khâu gộp RRF và chờ query lâu nhất hoàn thành.
- **Cost**: Không tốn chi phí bên ngoài.
- **Complexity**: Độ phức tạp cao vì phải đồng bộ hóa (Sync) ID giữa Qdrant và Inverted Index. Nếu một Chunk bị xóa ở Qdrant, phải xóa luôn ở BM25.
- **Extensibility**: Rất tốt. RRF cho phép trộn không giới hạn số lượng bộ máy tìm kiếm (có thể trộn thêm kết quả từ Graph Search).
- **Maintainability**: Khá vất vả nếu dùng 2 cơ sở dữ liệu khác nhau (Qdrant cho Dense, Elasticsearch cho BM25).
- **Testability**: Dễ test từng bộ retriever độc lập, sau đó test hàm RRF fusion.

## 6. Current Implementation
- **Trạng thái**: Đã implement (Simulation Layer). Lớp `BM25SparseIndexer` đang lưu Inverted Index hoàn toàn trên RAM thông qua thư viện `rank_bm25` (thuần Python).
- **Giới hạn**: 
  - Tokenizer của BM25 đang dùng hàm `split(" ")` khoảng trắng. Với tiếng Việt, nó sẽ coi "Nghị định" là 2 từ tách biệt "Nghị" và "định". Độ chính xác Keyword Search cực thấp.
  - Quá trình dựng (build) index BM25 trên RAM rất chậm với corpus lớn và sẽ mất hoàn toàn khi tắt ứng dụng.

## 7. Production Architecture
- Bỏ thư viện `rank_bm25` trên RAM.
- Chuyển Sparse Index sang tính năng **Qdrant Sparse Vectors** (hoặc dùng Elasticsearch). Đề xuất dùng luôn Qdrant Sparse để quy về 1 Database duy nhất, giảm độ phức tạp vận hành.
- **Bắt buộc** tích hợp Tokenizer tiếng Việt (`pyvi` hoặc `VnCoreNLP`) trước khi đưa vào Sparse Indexer.

## 8. Migration Guide
- **Thay component nào**: Xóa `BM25SparseIndexer`. Viết class `QdrantSparseIndexer` kế thừa `SparseIndexerInterface`.
- **Sửa file nào**: `sparse_indexer.py` và `qdrant_store.py`. Cập nhật `QdrantClient` để gọi hàm `query_batch` (cho phép prefetch cả sparse và dense trong 1 lượt mạng).
- **Dữ liệu**: Bắt buộc re-index lại hệ thống để tạo thêm cột Sparse Vector trong Qdrant.
- **Pipeline thay đổi**: Quá trình tạo Chunk sẽ phải chạy qua Tokenizer Tiếng Việt để sinh mảng tokens gửi lên Qdrant.

## 9. Impact Analysis
- **Chapter 3 (Query Pipeline)**: Mọi câu hỏi liên quan đến con số cụ thể ("Điều 50", "Năm 2023") sẽ được trả lời chính xác, giải quyết tận gốc vấn đề Dense Model hay nhầm lẫn số má.

## 10. Risks & Technical Debt
- **Rủi ro**: Qdrant Sparse Vectors mới hỗ trợ thuật toán SPLADE (thông qua HuggingFace BGE-M3), không phải chuẩn BM25 truyền thống, có thể cần test lại kỹ lưỡng về chất lượng.
- **Technical Debt**: Tokenizer hàm `split()` hiện tại là một "món nợ" khổng lồ, khiến BM25 gần như vô dụng với tiếng Việt ở bản Dev.

## 11. Future Roadmap
1. Simulation (Hiện tại): BM25 trên RAM (rank_bm25) với basic split.
2. Production: Qdrant Sparse Vectors + Tokenizer Tiếng Việt (`pyvi`).
3. Enterprise: Tinh chỉnh model SPLADE riêng cho tiếng Việt để tạo Sparse Vector chất lượng cao nhất.

## 12. References
- [Reciprocal Rank Fusion (RRF) in Information Retrieval](#)
- [Qdrant Sparse Vectors Documentation](#)
