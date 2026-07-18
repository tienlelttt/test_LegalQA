# LegalQA v2 - System Overview & Architecture Decision Records (ADRs)

Chào mừng bạn đến với dự án **LegalQA v2**! 

Tài liệu này là Cổng thông tin trung tâm (Central Hub), cung cấp cho bạn Bức tranh tổng thể về toàn bộ dự án, đồng thời lưu trữ danh sách các Quyết định Kiến trúc (ADRs) cốt lõi.

---

## BỨC TRANH TỔNG THỂ (SYSTEM OVERVIEW)

### 1. LegalQA giải quyết bài toán gì?
Hệ thống luật pháp Việt Nam vô cùng phức tạp với hàng chục ngàn văn bản chồng chéo, sửa đổi lẫn nhau. Việc tra cứu thủ công là một cơn ác mộng. Tuy nhiên, nếu dùng ChatGPT hay AI thông thường để hỏi luật, AI rất dễ "bịa ra" (hallucinate) số Điều hoặc nội dung luật không tồn tại, dẫn đến hậu quả pháp lý khôn lường.

**LegalQA v2** ra đời nhằm giải quyết bài toán đó. Nó là một hệ thống **RAG (Retrieval-Augmented Generation)** chuyên biệt cho pháp luật. Hệ thống không cho phép AI tự nhớ luật, mà buộc AI phải "Đọc tài liệu" (Context) từ một kho lưu trữ chính thống trước khi trả lời. Nếu không tìm thấy luật, hệ thống phải trả lời là "Không biết" thay vì "Bịa ra".

### 2. Kiến trúc tổng thể hoạt động như thế nào?
Dự án được chia làm 3 Module lớn (hoạt động độc lập, giao tiếp lỏng lẻo):

- **[Chapter 1] Document Parsing & Chunking**: Đóng vai trò "Nhà máy tinh chế". Nhận vào PDF/DOCX luật thô kệch, bóc tách cấu trúc (Chương, Điều, Khoản) bằng State Machine và Regex, và phân mảnh (Chunking) sao cho không làm vỡ ngữ cảnh pháp lý.
- **[Chapter 2] Vector Database & Embedding**: Đóng vai trò "Kho lưu trữ siêu tốc". Biến các văn bản tiếng Việt thành Ma trận số (Vector) và lưu vào Qdrant. Hỗ trợ tìm kiếm Hybrid (Vừa tìm ngữ nghĩa, vừa tìm đích danh số hiệu văn bản).
- **[Chapter 3] Query Pipeline**: Đóng vai trò "Người phục vụ khách hàng". Nhận câu hỏi, tìm văn bản từ Kho (Chapter 2), lọc văn bản hết hiệu lực, trộn Prompt, gọi AI sinh câu trả lời, và cuối cùng chạy qua một máy quét (Verification) để phát hiện và chặn đứng mọi "ảo giác".

### 3. Làm thế nào để khám phá dự án này?
Hãy bắt đầu bằng việc đọc `ENGINEERING_DOCS.md` của từng Chapter. Tại mỗi file, bạn sẽ tìm thấy **Phần I: Câu chuyện kiến trúc** (giải thích luồng code, mổ xẻ thuật toán) và **Phần II: ADRs** (lý do chọn công nghệ).

---

## DANH SÁCH QUYẾT ĐỊNH KIẾN TRÚC (ADR LOG)

Tài liệu này tổng hợp danh sách toàn bộ các Architecture Decision Records (ADRs) của dự án LegalQA. Mỗi ADR được đánh mã số theo Chapter và chứa nội dung chi tiết trong file `ENGINEERING_DOCS.md` của từng module tương ứng.

Toàn bộ ADR đều tuân thủ chuẩn Enterprise (12 mục).

---

## Chapter 1: Document Parsing & Chunking
*Vị trí chi tiết: [chapter-1-parsing/ENGINEERING_DOCS.md](./chapter-1-parsing/ENGINEERING_DOCS.md)*

- **ADR 1.1**: Lựa chọn phương pháp bóc tách cấu trúc (Regex/State Machine vs LLM - Đã loại bỏ hoàn toàn OCR).
- **ADR 1.2**: Chiến lược phân mảnh ngữ nghĩa (Adaptive Hierarchical Chunking vs Fixed-size Chunking).
- **ADR 1.3**: Chiến lược trích xuất siêu dữ liệu (Metadata Extraction Strategy).

---

## Chapter 2: Vector Database & Embedding
*Vị trí chi tiết: [chapter-2-vector-db/ENGINEERING_DOCS.md](./chapter-2-vector-db/ENGINEERING_DOCS.md)*

- **ADR 2.1**: Lựa chọn Vector Database (Qdrant vs Milvus vs Pinecone).
- **ADR 2.2**: Lựa chọn Embedding Model (MiniLM vs BGE-M3).
- **ADR 2.3**: Chiến lược Hybrid Search (Dense + Sparse BM25 + Reciprocal Rank Fusion).
- **ADR 2.4**: Chiến lược lưu trữ Knowledge Graph (Neo4j vs In-memory Simulation).

---

## Chapter 3: Query Pipeline
*Vị trí chi tiết: [chapter-3-query-pipeline/ENGINEERING_DOCS.md](./chapter-3-query-pipeline/ENGINEERING_DOCS.md)*

- **ADR 3.1**: Áp dụng Façade & Orchestrator Pattern cho Query Pipeline.
- **ADR 3.2**: Chiến lược Hiểu câu hỏi (Query Normalization & LLM Rewriter).
- **ADR 3.3**: Chiến lược Reranking và Rule-based Filtering (Cross-Encoder).
- **ADR 3.4**: Hệ thống Kiểm chứng Chống ảo giác (Verification Pipeline & NLI Groundedness).
- **ADR 3.5**: Quản lý Configuration (Settings Injection thay cho Magic Numbers).

---
*Tài liệu này là Single Source of Truth cho quá trình tra cứu lịch sử quyết định kiến trúc của toàn bộ dự án.*
