# Báo Cáo Trạng Thái Hệ Thống LegalQA v2 Hiện Tại

Dưới đây là báo cáo toàn diện về tình trạng mã nguồn và kiến trúc hiện tại của dự án LegalQA v2. 

## 1. Kiến Trúc Tổng Thể & Các Chapter Hiện Có

Dự án hiện tại được chia làm **3 Chapter** chính (tương ứng với 3 Khối nghiệp vụ).

1. **Chapter 1 (`chapter-1-parsing`)**: Xử lý đầu vào. Chịu trách nhiệm dọn rác, bóc tách cấu trúc Chương/Điều/Khoản bằng Regex, trích xuất siêu dữ liệu và phân tách văn bản thành các Chunks (Adaptive Chunking).
2. **Chapter 2 (`chapter-2-vector-db`)**: Indexing và Lưu trữ. Nhận các Chunks từ Chapter 1 và đưa vào 3 hệ thống: Vector DB (Dense), Inverted Index (BM25 Sparse), và Knowledge Graph.
3. **Chapter 3 (`chapter-3-query-pipeline`)**: Trả lời truy vấn. Tiếp nhận câu hỏi, áp dụng Hybrid Retrieval (tìm kiếm lai từ 3 nguồn lưu trữ trên), và sử dụng LLM để sinh câu trả lời kèm kiểm chứng (Groundedness & Citation).

## 2. Trạng Thái Mã Nguồn & Demo E2E

Hiện tại, mã nguồn đã kết nối thành công End-to-End Pipeline giữa các module (từ Parsing đến Indexing và Retrieval). Tuy nhiên, hệ thống đang sử dụng **Simulation Layers (Lớp giả lập)** cho các thao tác phụ thuộc vào hạ tầng bên ngoài, nhằm mục đích tiết kiệm chi phí, dễ dàng setup ở Local và phát triển MVP nhanh chóng.

### File Demo Chạy Được Ngay: `demo_e2e.py`
Bạn có thể chạy thử trực tiếp luồng End-to-End bằng lệnh:
```bash
python demo_e2e.py
```
**Luồng chạy của file demo này:**
1. **Mock Ingestion**: Đọc dữ liệu thô `luat_dat_dai.txt` bằng `MockPyMuPDFIngestor`.
2. **Parsing & Chunking**: Làm sạch và trích xuất Metadata (dùng giả lập `MockLLMMetadataExtractor`), sau đó chia Chunk.
3. **Storage Giả Lập**:
   - Sử dụng Vector DB dạng In-Memory thay vì Qdrant.
   - Sử dụng Sparse Indexer BM25 tính điểm trực tiếp.
   - Sử dụng Knowledge Graph dạng In-Memory (`MemoryGraphRepository`) thay vì Neo4j.
4. **Hybrid Retrieval**: Thiết lập 3 bộ tìm kiếm (Dense, Sparse, Graph) và truy vấn thử câu hỏi "Sở hữu đất đai thuộc về ai?", in ra top kết quả.

## 3. Lộ Trình Triển Khai Tiếp Theo (Roadmap)

Tài liệu thiết kế `kien_truc_legalqa_hoan_chinh.md` đã quy định rõ lộ trình thay thế dần các Lớp giả lập bằng các hệ thống thật:

- **Bước tiếp theo (Giai đoạn 1 - Đang triển khai)**: Thay thế `MockLLMMetadataExtractor` bằng `GeminiMetadataExtractor` (Sử dụng API Gemini thực sự) và thay thế việc đọc text chay bằng `PyMuPDF` thực thụ để lấy Layout Analysis. (Tôi đã tạo bản kế hoạch `implementation_plan.md` cho việc này).
- **Giai đoạn 2 (Retrieval Nâng Cao)**: Tích hợp Elasticsearch cho thuật toán BM25 và Neo4j cho Knowledge Graph. Cài đặt các bước xác thực Rerank và Chống ảo giác (Anti-hallucination).
- **Giai đoạn 3 & 4 (Truy Vấn Thông Minh & Ops)**: Cắm LLM Generator, thêm Cache, và thiết lập luồng Feedback.

## 4. Tổng Kết
Hệ thống LegalQA hiện tại đang có **bộ khung kỹ thuật rất vững chắc và đúng chuẩn kiến trúc**. Mã nguồn chạy trơn tru thông qua các bộ Mock. Nhiệm vụ hiện tại chỉ là thay thế từng bộ phận Mock bằng các công nghệ thật (ví dụ: cắm API Key Gemini, dựng Docker chứa Neo4j/Qdrant) theo đúng định hướng đã vạch ra.
