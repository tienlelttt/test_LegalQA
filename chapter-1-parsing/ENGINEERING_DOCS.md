# Engineering Docs: Legal Document Parsing & Chunking Module

**Giai đoạn**: Document Pipeline (Bước 1)  
**Kiến trúc tương thích**: LegalQA v2

> [!CAUTION]
> **ĐÂY KHÔNG PHẢI LÀ CẤU HÌNH PRODUCTION.**
> Mã nguồn hiện tại được thiết kế như một **Simulation Layer (Lớp mô phỏng)** để các kỹ sư có thể phát triển logic và kiểm thử ở môi trường Local mà không cần tốn chi phí API hay setup hạ tầng phức tạp. Việc hiểu rõ ranh giới giữa bản hiện tại và bản Production giúp kỹ sư không bị lầm tưởng về năng lực thực sự của hệ thống (ví dụ: hiện tại không thể trích xuất metadata phức tạp hay đọc file ảnh scan). Mọi tài liệu thiết kế bắt buộc phải được cập nhật đồng bộ mỗi khi mã nguồn được triển khai hoặc thay đổi.

## CHANGELOG
- **Thay đổi**: Tái cấu trúc tài liệu kiến trúc sang mô hình 2-Tier theo chuẩn mới (Tier 1: Tổng quan chuyên sâu, Tier 2: ADR độc lập).
- **Lý do lệch**: Tài liệu cũ thiếu vắng phân tích rủi ro dài hạn, hướng dẫn di chuyển (Migration) và phân tích trade-offs chi tiết theo 8 trục.
- **Kiến trúc cũ**: Một file duy nhất chứa cả tổng quan và ADR vắn tắt.
- **Kiến trúc mới**: File này (`ENGINEERING_DOCS.md`) đóng vai trò Tier 1 (9 mục chuẩn). Các ADR đã được di dời và mở rộng trong thư mục `adr/`.
- **Kế hoạch migration**: Đã dọn dẹp các keyword lỗi thời. Không phá vỡ luồng code hiện tại.

---

## 1. Giải thích bài toán tổng thể của dự án
Văn bản pháp luật Việt Nam có cấu trúc phân cấp cực kỳ nghiêm ngặt: `Chương` → `Mục` → `Điều` → `Khoản` → `Điểm`. 

Nếu chúng ta sử dụng các thư viện cắt chữ thông thường (như `RecursiveCharacterTextSplitter` của LangChain), một câu văn có thể bị cắt làm đôi, hoặc một Điểm a) bị tách rời khỏi Điều khoản chứa nó. 
**Hậu quả:**
- **Mất bối cảnh cục bộ**: LLM không biết Điểm a) này thuộc về "Điều kiện áp dụng" hay "Ngoại lệ".
- **Ảo giác (Hallucination)**: LLM sinh câu trả lời bịa ra số Điều hoặc tham chiếu sai lệch do không nhận diện được đoạn text thuộc về đơn vị pháp lý nào.
- **Mù Viện dẫn (Blind Citations)**: Hệ thống không thể biết văn bản nào đang thay thế/sửa đổi văn bản nào nếu không trích xuất được Metadata chính xác.

**Sứ mệnh của Module 1**: Trở thành một "nhà máy tinh chế", biến các file PDF/DOCX thô kệch thành các đoạn văn bản (Chunks) gọn gàng. Mỗi Chunk không chỉ chứa nội dung mà còn "cõng" theo toàn bộ bối cảnh của nó (Thuộc Điều mấy? Tên Điều là gì? Của văn bản nào? Còn hiệu lực không?).

## 2. Kiến trúc tổng thể & Luồng dữ liệu
Quá trình chuyển đổi dữ liệu đi qua 4 pipeline nhỏ:

**Bước 1: Cleaning (`src/cleaner.py`)**
- **Mục đích**: Loại bỏ các đoạn văn bản rác (header/footer, số trang, lỗi encoding) gây nhiễu cho bước Parsing.
- **Chi tiết thuật toán**: Sử dụng Regex Whitelist. Thay vì xóa mù quáng bằng `\d+` (có thể vô tình xóa mất "Điều 1"), hệ thống sẽ dò quét và "bảo vệ" các pattern quan trọng như `Điều \d+`, `Khoản \d+`, hoặc số hiệu văn bản trước. Sau đó mới thực hiện thao tác xóa rác.

**Bước 2: Structure Parsing (`src/parser.py`)**
- **Mục đích**: Chuyển đổi văn bản phẳng thành dạng cây phân cấp (Syntax Tree).
- **Chi tiết thuật toán**: Sử dụng **State Machine (Máy trạng thái)** kết hợp Regex. Máy trạng thái đọc văn bản từng dòng. Nếu gặp dòng bắt đầu bằng `^Điều \d+\.`, nó đổi trạng thái sang "Đang ở Điều X". Mọi dòng tiếp theo sẽ được nhét vào Điều X cho đến khi gặp pattern của Điều X+1 hoặc Khoản.

**Bước 3: Metadata Extraction (`src/extractor.py`)**
- **Mục đích**: Trích xuất siêu dữ liệu (Số hiệu, Ngày ban hành, Tình trạng hiệu lực, Quan hệ thay thế).
- **Chi tiết thuật toán**: Dùng Regex bắt các định dạng cố định (như số hiệu `45/2023/NĐ-CP`). Ở các phần nội dung tự do (như đoạn kết thúc nói về hiệu lực), thiết kế gọi API LLM trả về cấu trúc JSON.

**Bước 4: Adaptive Chunking (`src/chunker.py`)**
- **Mục đích**: Chia nhỏ văn bản cho Vector DB nhưng không làm mất ngữ cảnh.
- **Chi tiết thuật toán**: Dùng "Điều" làm đơn vị gốc. Nếu Điều vượt quá giới hạn token (vd: 512), hệ thống đệ quy xuống "Khoản", "Điểm". Khi tách nhỏ, thuật toán lấy tiêu đề của Node cha dán thẳng vào đầu Node con (Prepend Context).

## 3. Giải thích Quyết định Kiến trúc & Phân tích Implementation

*(Xem chi tiết đầy đủ tại thư mục `adr/`)*

### 3.1. Parsing Strategy (State Machine + Regex)
- **a. Lý thuyết chuẩn**: Dùng LLM bóc tách thông tin thô hoặc NLP chuyên dụng (Named Entity Recognition - NER) kết hợp với Graph Database để giữ cấu trúc.
- **b. Alternatives Considered**:
  - *LLM-based Parsing*: Xử lý tốt văn bản lộn xộn, nhưng quá đắt đỏ và cực kỳ chậm, rủi ro sinh ảo giác làm biến dạng nguyên văn luật. Bỏ qua.
  - *Regex tĩnh thuần túy*: Nhanh nhưng không duy trì được trạng thái ngữ cảnh (đang ở Chương mấy). Bỏ qua.
- **c. Implementation hiện tại**: Dùng Rule-based State Machine kết hợp Regex.
- **d. Phát triển Production**: Đã loại bỏ hoàn toàn OCR theo Ground Truth để tinh gọn hệ thống. Chỉ xử lý văn bản có text layer. Có cơ chế Fallback gọi LLM chỉ khi Regex thất bại.
- **e. Trade-offs**: 
  - *Perf*: Cực nhanh (<0.1s/file). *Memory*: Tối ưu. *Latency*: Không có. *Cost*: $0. 
  - *Complexity*: Quản lý Rule-set Regex khá mệt mỏi. *Maintainability*: Khó. *Testability*: Dễ test. *Extensibility*: Tốt.
- **f. Ảnh hưởng chất lượng**: Hoạt động xuất sắc với file Text. Nhược điểm là hiện tại trả về rỗng nếu gặp file Scan.
- **g. References**: ADR-101. Design Patterns (Gang of Four).

### 3.2. Adaptive Chunking Strategy
- **a. Lý thuyết chuẩn**: Parent-Child Retrieval (Lưu Chunk nhỏ vào VectorDB, lưu Chunk to vào Document Store).
- **b. Alternatives Considered**:
  - *Fixed-size Chunking*: Phá vỡ hoàn toàn ngữ cảnh pháp lý. Bỏ qua.
  - *Document-level Embedding*: Vượt quá Context Window của model. Bỏ qua.
- **c. Implementation hiện tại**: Adaptive Hierarchical Chunking nhưng dùng shortcut "Prepend String" (Dán cứng chuỗi tiêu đề Điều vào đầu của Khoản). Không dùng DB lưu Parent.
- **d. Phát triển Production**: Cần Document Store (MongoDB) để lưu Parent. Khi query hit Child, gọi MongoDB trả về Parent.
- **e. Trade-offs**: 
  - *Perf*: Nhanh. *Memory*: Tốn RAM 10-15% do lặp chuỗi. *Latency*: Thấp. *Cost*: $0.
  - *Complexity*: Trung bình. *Maintainability*: Tốt. *Testability*: Dễ. *Extensibility*: Cao.
- **f. Ảnh hưởng chất lượng**: Tránh được ảo giác mất ngữ cảnh, nhưng làm tốn token thừa khi Search và Generation do prefix trùng lặp liên tục.
- **g. References**: ADR-102. LlamaIndex Parent-Child Retrieval.

### 3.3. Metadata Extraction Strategy
- **a. Lý thuyết chuẩn**: LLM cấu hình JSON Mode (Structured Output).
- **b. Alternatives Considered**:
  - *Rule-based NLP*: Bất lực trước diễn đạt tự do phức tạp ("Bãi bỏ khoản 1 điều 2..."). Bỏ qua.
  - *Dùng LLM toàn bộ file*: Chậm, tốn kém hàng trăm ngàn token/file. Bỏ qua.
- **c. Implementation hiện tại**: `MockLLMMetadataExtractor` (Trả về dữ liệu JSON hardcode giả lập).
- **d. Phát triển Production**: Chỉ cắt 2000 từ đầu và cuối file gửi cho Gemini/GPT-4o-mini lấy JSON.
- **e. Trade-offs**:
  - *Perf*: Chậm hơn (chờ API). *Memory*: Nhỏ. *Latency*: Tăng vài giây. *Cost*: Vài cent/file.
  - *Complexity*: Phức tạp (cần cấu hình Pydantic). *Maintainability*: Phụ thuộc Cloud Provider. *Testability*: Cần Mock. *Extensibility*: Cực cao.
- **f. Ảnh hưởng chất lượng**: Bản Dev đang dùng Mock data nên "mù" hoàn toàn trước dữ liệu PDF thật (không biết file đó còn hiệu lực hay không).
- **g. References**: ADR-103. OpenAI Structured Output Docs.

## 4. Những điểm khác so với kế hoạch kiến trúc ban đầu
- **Trích xuất Text (PDF Ingestion)**:
  - *Thiết kế ban đầu*: Dùng `PyMuPDF` để đọc PDF trực tiếp và giữ nguyên layout (tọa độ, font-size).
  - *Thực tế làm tắt*: Đang dùng `MockPyMuPDFIngestor` đọc thẳng từ file Text (`.txt`).
  - *Nhược điểm*: Không bắt được font-size, mất tính năng nhận diện Heading bằng Layout Analysis.
  - *Roadmap*: Cắm thư viện `PyMuPDF` (fitz) thực tế vào Ingestion Pipeline.
- **Xử lý Ingestion (Message Queue)**:
  - *Thiết kế ban đầu*: Ingest qua RabbitMQ/Kafka bất đồng bộ.
  - *Thực tế làm tắt*: Vòng lặp tuần tự Synchronous.
  - *Nhược điểm*: Treo hệ thống (blocking) nếu Ingest hàng nghìn file một lúc.
  - *Roadmap*: Cài đặt Celery Worker.
- **LLM Metadata Extraction**:
  - *Thiết kế ban đầu*: Dùng Model Gemini 1.5.
  - *Thực tế làm tắt*: Trả về dữ liệu cứng bằng Mock Class.
  - *Nhược điểm*: Phá hỏng bước Filter ở Module 2/3 nếu áp dụng cho dữ liệu ngoài đời thực.
  - *Roadmap*: Cắm API thật.

## 5. Chiến lược Phần cứng & GPU (GPU Strategy)
Kiến trúc sư thiết kế hạ tầng Production cho Module 1 cần cấp phát tài nguyên như sau:
- **Tầng Parser & Chunker**: Hoàn toàn chạy trên CPU. Yêu cầu Multi-core (ví dụ: 16 cores) để chạy song song nhiều worker (Multiprocessing). Không cần GPU.
- **Tầng Metadata Extractor (LLM)**: 
  - Nếu dùng SaaS (OpenAI/Gemini): Chỉ tốn băng thông mạng.
  - Nếu dùng Self-hosted (e.g., Qwen2.5-3B, mô hình <= 4B): Cần **1x GPU NVIDIA T4 (16GB VRAM)** chạy qua vLLM (Tuyệt đối không dùng LLM >= 7B).

## 6. Production Roadmap
1. **Bước 1 (LLM Integration)**:
   - *Hành động*: Tạo class `GeminiMetadataExtractor` kế thừa `MetadataExtractorInterface`. Bổ sung Pydantic Validation & Tenacity Retry.
   - *Điều kiện hoàn thành*: Parsing thành công 100 văn bản mẫu thực tế có đầy đủ metadata.
2. **Bước 2 (Real PDF Ingestion)**:
   - *Hành động*: Cài đặt `PyMuPDF` (`fitz`). Viết `PyMuPDFIngestor` xử lý Layout Analysis.
   - *Điều kiện hoàn thành*: Đọc thành công file PDF thật, trích xuất cấu trúc dựa trên tọa độ, font-size mà không cần dựa hoàn toàn vào Regex.
3. **Bước 3 (Asynchronous Queue)**:
   - *Hành động*: Đưa toàn bộ hàm xử lý file vào Celery Workers. Cắm Message Broker (Redis/RabbitMQ).
   - *Điều kiện hoàn thành*: Submit 1 vạn trang PDF qua API không làm sập server chính.

## 7. Impact Analysis toàn hệ thống
Nếu thay đổi bất kỳ cơ chế Chunking hoặc Parsing nào ở Module 1, ảnh hưởng sẽ lan rộng:
- **Chapter 2 (Vector DB)**: Nếu thuật toán Chunking đổi (ví dụ giảm max tokens), lượng vector đẩy lên Qdrant sẽ tăng vọt, tiêu tốn nhiều RAM của DB. Cần Re-index toàn bộ dữ liệu (không thể xài chunk cũ - chunk mới lẫn lộn).
- **Chapter 3 (Query Pipeline)**: Mọi sự thay đổi về Metadata format (JSON Schema) ở Module 1 sẽ lập tức làm gãy logic Filter (Loại văn bản hết hiệu lực) ở Module 3. Cần test E2E cực kỳ cẩn thận.

## 8. Risks & Technical Debt tổng hợp
- **Rủi ro phụ thuộc Rule (Brittle Rules)**: Văn bản pháp luật nhà nước thường xuyên đổi chuẩn format (vd: đổi từ `.VnTime` sang Unicode, hoặc đổi cách thụt đầu dòng). State Machine hiện tại rất dễ bị vỡ trận nếu gặp format quá dị biệt.
- **Tech Debt (Tokenization)**: Hàm đếm token hiện tại dựa trên số từ (`len(text.split())`) để mô phỏng, thay vì dùng Tokenizer chuẩn (ví dụ tiktoken). Dễ dẫn đến rủi ro "vượt token limit" của Qdrant/LLM ở Production.
- **Tech Debt (Retry Mechanism)**: Code hiện tại chưa thiết kế Error Boundary chuẩn cho Ingestion. Lỗi 1 file có thể làm chết cả quá trình quét thư mục.

## 9. Migration Guide (Cho các bước Roadmap)
- **Bước 1 (LLM Integration)**:
  - *Thay đổi*: Inject `GeminiMetadataExtractor` thay cho bản Mock. Sửa file `src/extractor.py`.
  - *Dữ liệu*: Bắt buộc chạy lại lệnh Re-index từ file thô (Raw PDFs).
  - *Rollback*: Đổi Dependency Injection config về lại `RegexMetadataExtractor`.
- **Bước 2 (Real PDF Ingestion)**:
  - *Thay đổi*: Cài thêm System Dependencies (`PyMuPDF`). Sửa `src/ingestor.py` bóc tách layout.
  - *Backward Compatibility*: Các file text-based thô có thể rẽ nhánh dùng Ingestor cũ nếu cần, giữ độ ổn định.
- **Bước 3 (Async Queue)**:
  - *Thay đổi*: Cần dựng thêm Redis/RabbitMQ qua Docker. Khởi động thêm Celery Worker process.
  - *Rollback*: Chuyển cấu hình `CELERY_TASK_ALWAYS_EAGER = True` để nó chạy Synchronous trở lại.
