# LEGALQA V2 - MASTER SYSTEM GUIDELINES & CONSTRAINTS

Tài liệu này đóng vai trò là **Bộ Ràng Buộc Cứng (Master README)** cho toàn bộ hệ thống LegalQA v2. Mọi module, mọi tính năng được phát triển (từ Bước 1 đến Bước N) **BẮT BUỘC** phải tuân thủ nghiêm ngặt các quy định và luồng nghiệp vụ trong tài liệu này để đảm bảo sự xuyên suốt, độ chính xác tuyệt đối và loại bỏ hoàn toàn rủi ro ảo giác (hallucination) trong lĩnh vực pháp lý.

---

## 1. MỤC TIÊU TỐI THƯỢNG CỦA HỆ THỐNG
LegalQA v2 không phải là một chatbot trò chuyện thông thường. Đây là một hệ thống **Retrieval-Augmented Generation (RAG) cấp độ Production** dành riêng cho pháp luật Việt Nam.
- **Thà từ chối trả lời ("Không đủ căn cứ") còn hơn trả lời sai hoặc bịa luật.**
- **Mọi câu trả lời phải được trích dẫn chính xác đến từng Điều, Khoản, Điểm.**

---

## 2. LUỒNG NGHIỆP VỤ XUYÊN SUỐT (END-TO-END FLOW)
Toàn bộ hệ thống được chia thành 3 khối hoạt động song song. Bất kỳ mã nguồn nào được viết ra đều phải thuộc về 1 trong 3 khối này:

### Khối 1: Document Pipeline (Offline Indexing)
- **Chapter 1: Parsing & Chunking** -> Làm sạch văn bản, bóc tách cấu trúc (Chương/Điều/Khoản/Điểm), trích xuất viện dẫn, phân mảnh (Hierarchical Chunking).
- **Chapter 2: Vectorization & Indexing** -> Đưa Chunks vào 3 kho lưu trữ: Vector DB (Dense Embedding), Elasticsearch/OpenSearch (BM25 Sparse), và Neo4j (Knowledge Graph cho quan hệ liên văn bản).

### Khối 2: Query Pipeline (Online Answering)
- **Bước 1: Query Understanding** -> Chuẩn hóa câu hỏi, nhận diện thực thể (NER), lọc metadata.
- **Bước 2: Hybrid Retrieval** -> Tìm kiếm đa luồng (BM25 + Dense + Graph) và gộp kết quả bằng Reciprocal Rank Fusion (RRF).
- **Bước 3: Cross-Encoder Reranker** -> Xếp hạng lại, đánh tụt điểm hoặc loại bỏ hoàn toàn văn bản "Hết hiệu lực".
- **Bước 4: LLM Generation & Verification** -> Dựng Prompt với Legal Constraints -> LLM sinh câu trả lời -> **Kiểm chứng Groundedness & Citation** -> Trả kết quả.

### Khối 3: Ops Layer (Continuous Operation)
- Quản lý Incremental Indexing (cập nhật luật mới/sửa đổi).
- Caching 3 lớp (Semantic, Retriever, LLM).
- Vòng lặp phản hồi (Feedback Loop) có chuyên gia pháp lý kiểm duyệt.

---

## 3. CÁC RÀNG BUỘC CỨNG (STRICT CONSTRAINTS) 
Bất kỳ Pull Request (PR) hay Module nào vi phạm các quy tắc sau sẽ bị loại bỏ:

### 3.1. Ràng buộc về Xử lý dữ liệu (Ingestion & Parsing)
1. **KHÔNG DÙNG OCR**: Các văn bản luật hiện hành đã được số hóa. Bắt buộc dùng `PyMuPDF` hoặc các thư viện trích xuất text/layout trực tiếp.
2. **KHÔNG DÙNG LLM CHO BƯỚC PARSING**: Việc bóc tách cấu trúc Chương/Điều/Khoản phải được thực hiện bằng **Regex và Rule-based State Machine** để đảm bảo độ chính xác 100% và tiết kiệm chi phí/thời gian.
3. **CHUNK THEO NGỮ NGHĨA (SEMANTIC), KHÔNG CHUNK THEO SIZE**: Tuyệt đối không dùng `RecursiveCharacterTextSplitter` với chunk_size cố định. Phải chia theo cấu trúc phân cấp (Điều → Khoản → Điểm). Chỉ khi văn bản quá dài mới dùng Sliding Window Fallback.

### 3.2. Ràng buộc về Tìm kiếm (Retrieval)
1. **BẮT BUỘC HYBRID RETRIEVAL**: Không bao giờ chỉ dùng mỗi Dense Embedding. Phải kết hợp BM25 (để bắt chính xác số Điều, số hiệu văn bản) và dùng RRF để hợp nhất.
2. **LỌC METADATA TRƯỚC (PRE-FILTERING)**: Trạng thái hiệu lực của văn bản (`status = effective`) phải được đưa vào bộ lọc trước hoặc trong quá trình Rerank để chống truy xuất luật cũ (trừ khi user cố tình hỏi).

### 3.3. Ràng buộc về Sinh văn bản (Generation) & Chống Ảo giác
1. **KHÔNG BAO GIỜ TIN TƯỞNG TUYỆT ĐỐI VÀO LLM**: LLM (dù là mô hình lớn hay nhỏ) đều có thể sinh ảo giác số liệu.
2. **HAI TẦNG KIỂM CHỨNG BẮT BUỘC**:
   - **Groundedness Check**: Nội dung trả lời có thực sự nằm trong Chunk ngữ cảnh không?
   - **Citation Verification**: Số Điều/Khoản LLM trích dẫn có khớp chính xác tuyệt đối với Metadata của Chunk đầu vào không?
3. **FAIL-SAFE**: Nếu 1 trong 2 bước kiểm chứng trên thất bại, hệ thống phải trả về câu mặc định: *"Hệ thống không tìm đủ căn cứ rõ ràng để trả lời chính xác câu hỏi này"* thay vì cố đoán.

### 3.4. Ràng buộc về Kỹ thuật & Coding
1. **MÔI TRƯỜNG UTF-8 TỰ ĐỘNG**: Luôn thêm code ép hệ thống (như `sys.stdout.reconfigure(encoding='utf-8')`) hoặc sử dụng `.env` để cấu hình chuẩn Tiếng Việt, không để vỡ font trên console Windows.
2. **Pydantic Validation**: Mọi dữ liệu luân chuyển giữa các pipeline (như Output của Parser, Input của Chunker) đều phải đi qua model của Pydantic để validate kiểu dữ liệu.
3. **100% Unit Test & Benchmark**: Mỗi logic mới thêm vào phải có file test tương ứng trong thư mục `tests/` và chạy thành công trên mô hình Mock Data.
4. **Dọn dẹp Worktree (Clean Worktree)**: Bắt buộc dọn dẹp, xóa bỏ các file rác, file tạm, log, hoặc script chạy thử (scratch files) sinh ra trong quá trình làm việc. Chỉ lưu giữ các file thực sự có giá trị sử dụng và đã được tổ chức đúng cấu trúc dự án.

---

## 4. QUY TRÌNH PHÁT TRIỂN & CHUẨN HÓA THƯ MỤC
- **ĐIỀU KIỆN TIÊN QUYẾT BẮT BUỘC**: Bất kỳ kỹ sư nào tham gia dự án đều PHẢI đọc kỹ file kiến trúc tổng thể `docs/kien_truc_legalqa_hoan_chinh.md` trước khi viết bất kỳ dòng code nào.
- **Shared Resource Principle (Nguyên tắc tài nguyên dùng chung)**:
  - Chỉ có một nguồn dữ liệu chuẩn (`data/`) ở gốc dự án cho toàn bộ hệ thống (gồm `raw`, `processed`, `mock`, `benchmark`, `sample_queries`).
  - Các chapter **tuyệt đối không được sao chép hoặc tự lưu trữ dữ liệu riêng**.
  - Các script trong thư mục `examples/` hoặc `benchmark/` của từng chapter phải đọc dữ liệu từ kho `data/` chung qua module `shared/paths.py`.
- Mọi module mới (ví dụ Chapter 2, Chapter 3) phải tạo thư mục riêng biệt theo quy chuẩn của Chapter 1 (gồm `src/`, `tests/`, `examples/`, `benchmark/`).
- **Chuẩn hóa tài liệu bắt buộc cho MỖI module (Mô hình 2-Tier)**:
  - `README.md`: Trở về đúng chức năng là một bảng **Quickstart**. Chỉ tập trung giải thích cấu trúc thư mục hiện tại, hướng dẫn cài đặt, cách chạy Demo và Unit Test. Nó phải chứa liên kết dẫn thẳng sang `ENGINEERING_DOCS.md` và thư mục `adr/` cho ai muốn tìm hiểu sâu.
  - `ENGINEERING_DOCS.md` (Tier 1): **Bắt buộc** phải được tạo mới trong từng module. Đây là tài liệu kỹ thuật đi sâu vào phân tích bài toán, kiến trúc tổng thể, lộ trình Production và đánh giá rủi ro (để bất kỳ ai khi nhìn vào là hiểu được toàn cảnh hệ thống).
  - Thư mục `adr/` (Tier 2): **Bắt buộc**. Nơi lưu trữ các file Architecture Decision Records (ADR) độc lập, giải thích cặn kẽ từng quyết định kiến trúc, đánh giá Trade-offs (8 trục) và phân tích ảnh hưởng (Impact Analysis).
- Tuyệt đối không lưu file thừa (file temp, file `.zip`, script cài đặt `get-pip.py`) vào trong repo hệ thống.
- Cấu hình chung cho toàn project (nếu có) phải được đặt ở thư mục root (định dạng `.env` hoặc `settings.yaml`).

Tài liệu này là "Kim chỉ nam" kỹ thuật cao nhất. Tuân thủ tài liệu này là cách duy nhất để xây dựng một sản phẩm LegalQA thực sự dùng được trong Production.

---

## 5. CÁC LỚP MÔ PHỎNG (SIMULATION LAYERS) & MIGRATION GUIDE

Để đảm bảo hệ thống luôn có thể chạy (runnable) ở mọi giai đoạn phát triển ngay cả khi hạ tầng Production (Neo4j, Elasticsearch) chưa sẵn sàng, dự án sử dụng các **Simulation Layers (Lớp mô phỏng)**.

> **NGUYÊN TẮC QUAN TRỌNG:** 
> - Code luôn gọi qua Interface.
> - Tuyệt đối không hardcode bỏ qua các Pipeline (Graph, Sparse).
> - Khi nâng cấp, KHÔNG SỬA CODE ở Pipeline, chỉ đổi Dependency Injection (thay implementation model).

### Danh sách các Module đang dùng Simulation (Trạng thái hiện tại)

| Thành phần | Interface | Simulation Class đang dùng | Giải pháp Production tương lai | Điều kiện Migration |
| :--- | :--- | :--- | :--- | :--- |
| **PDF Ingestor** | `BaseIngestor` | `MockPyMuPDFIngestor` (đọc từ `.txt`) | `PyMuPDFIngestor` (dùng fitz bóc tách PDF gốc) | Khi có luồng cung cấp tài liệu PDF thực tế |
| **Metadata LLM** | `MetadataExtractorInterface` | `MockLLMMetadataExtractor` (trả về JSON tĩnh) | `GeminiMetadataExtractor` (dùng LLM extract) | Khi có API Key & LLM Router sẵn sàng |
| **Sparse Index** | `BaseSparseIndexer` | `BM25SparseIndexer` (Tính điểm từ khóa thô) | `QdrantSparseIndexer` / `Elasticsearch` | Khi CSDL Vector setup xong BM25 native |
| **Knowledge Graph**| `GraphRepository` | `MemoryGraphRepository` (Dictionary in-memory) | `Neo4jRepository` | Khi có server Neo4j cài đặt |

### Hướng dẫn Migration (Nâng cấp)

1. **Giữ nguyên Interface**: Kỹ sư viết class mới (ví dụ: `Neo4jRepository`) bắt buộc kế thừa `GraphRepository`.
2. **Khai báo cấu hình mới**: Thay vì khởi tạo `graph_store = MemoryGraphRepository()`, đổi thành `graph_store = Neo4jRepository(uri, user, pass)`.
3. **Tuyệt đối không sửa IndexPipeline**: `IndexPipeline` đã chuẩn hóa truyền dữ liệu, không được thay đổi cấu trúc `Chunk` hoặc `Metadata` trong lúc đổi cơ sở dữ liệu.
