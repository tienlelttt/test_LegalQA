# Engineering Docs: Query Pipeline (Module 3)

**Giai đoạn**: Query Pipeline (Bước 3 - Online Answering)  
**Kiến trúc tương thích**: LegalQA v2

> [!CAUTION]
> **ĐÂY KHÔNG PHẢI LÀ CẤU HÌNH PRODUCTION.**
> Mã nguồn hiện tại là một **Simulation Layer (Lớp mô phỏng)** được thiết kế để kiểm thử toàn bộ dòng chảy dữ liệu (End-to-End data flow) tại môi trường Local. Hầu hết các chốt chặn AI (LLM, Reranker, NLI Verifier) đang được "mock" (giả lập bằng Rule/Regex chữ). Việc hiểu rõ điều này giúp Kiến trúc sư không bị lầm tưởng về năng lực thực sự của hệ thống hiện tại. Dữ liệu đầu ra trong code hiện tại chỉ mang tính minh họa kiến trúc. Mọi tài liệu thiết kế bắt buộc phải được cập nhật đồng bộ mỗi khi mã nguồn thay đổi.

## CHANGELOG
- **Thay đổi**: Tái cấu trúc tài liệu kiến trúc sang mô hình 2-Tier theo chuẩn mới (Tier 1: Tổng quan chuyên sâu, Tier 2: ADR độc lập).
- **Lý do lệch**: Tài liệu cũ gom chung tổng quan và các quyết định thiết kế dài dòng, thiếu phân tích Trade-offs chi tiết 8 trục, thiếu Impact Analysis và phần Hướng dẫn Migrate.
- **Kiến trúc cũ**: Một file duy nhất.
- **Kiến trúc mới**: File này đóng vai trò Tier 1. Các ADR (Quyết định cụ thể về Orchestrator, Rewriter, Reranker, NLI Verifier, Configuration) đã được tách ra thư mục `adr/` và viết lại hoàn chỉnh theo chuẩn 12-section.

---

## 1. Giải thích bài toán tổng thể của dự án
Nếu Module 1 và Module 2 là hệ thống "Nhập kho" (Offline Ingestion), thì Module 3 chính là "Cửa hàng" phục vụ khách hàng (Online Query Pipeline).

Thách thức cực lớn trong Domain Pháp lý: **Sự không hoàn hảo của người dùng và sự "nguy hiểm" của LLM**.
- Người dùng hỏi sai ngữ pháp, dùng từ viết tắt, khẩu ngữ ("Cho hỏi luật đđ năm 24..."). 
- Nếu ném nguyên câu đó vào Vector DB, kết quả sẽ nhiễu loạn.
- Ngay cả khi lấy được text chuẩn, LLM (Generative AI) vẫn có nguy cơ mắc bệnh "ảo giác" (Hallucination) - tự bịa ra Điều, Khoản không hề tồn tại để làm vừa lòng người dùng. Trả lời sai luật nguy hiểm gấp ngàn lần việc từ chối trả lời.

**Sứ mệnh của Module 3**:
1. Đón nhận câu hỏi, làm sạch và "hiểu" ý định của người dùng.
2. Điều phối quá trình tìm kiếm (Gọi sang Module 2).
3. Lọc lại kết quả cực kỳ khắt khe (chỉ lấy Top 5 sắc bén nhất, loại bỏ văn bản hết hiệu lực).
4. Sinh câu trả lời bằng LLM.
5. **Chốt kiểm duyệt (Verification)**: Dập tắt ảo giác bằng AI chuyên dụng trước khi gửi cho user.

## 2. Kiến trúc tổng thể & Luồng dữ liệu
Hệ thống là một băng chuyền nhà máy được điều phối bởi **Query Orchestrator** đi qua 7 bước tuần tự:

**Trạm trung tâm: Query Orchestrator (`src/orchestrator.py`)**
Nhạc trưởng điều phối luồng dữ liệu, bọc 7 bước lại thành 1 hàm `ask(query)` duy nhất (Façade Pattern). Nhận tất cả Interfaces vào Constructor, đo lường thời gian và quản lý ngoại lệ.

**Bước 1: Query Normalization & Rewriting (`src/query_understanding.py`)**
Làm sạch (xóa rác) và "viết lại" câu hỏi thô thành câu truy vấn chuẩn mực.

**Bước 2: Retrieval (Gọi Module 2)**
Bắn câu hỏi xuống HybridRetriever lấy Top 30 ứng viên (Chunks).

**Bước 3: Reranking (`src/reranker.py`)**
Chạy Hard-rule lọc rác pháp lý (trạng thái hết hiệu lực). Phần còn lại đưa vào Cross-Encoder chấm điểm chéo. Lấy Top 5.

**Bước 4 & 5: Context & Prompt Building (`src/prompt_builder.py`)**
Đếm token để đảm bảo không bị vượt giới hạn, nhét 5 Chunks vào thẻ `<context>` tạo khung Prompt.

**Bước 6: Generation (`src/generator.py`)**
Gọi LLM sinh câu trả lời.

**Bước 7: Verification (`src/verifier.py`)**
Chốt kiểm duyệt chống ảo giác. Tách câu, đối chiếu NLI. Bắt lỗi Citation. Nếu lỗi, đánh cờ `is_grounded = False`.

## 3. Giải thích Quyết định Kiến trúc & Phân tích Implementation

*(Xem chi tiết đầy đủ tại thư mục `adr/`)*

### 3.1. Façade & Orchestrator Pattern
- **a. Lý thuyết chuẩn**: Agent Router tự trị (LLM tự quyết định rẽ nhánh logic).
- **b. Alternatives Considered**: 
  - *Monolithic Function*: Khó bảo trì, không test được.
  - *Agent Router*: Rủi ro pháp lý cao nếu LLM bị jailbreak và bỏ qua vòng kiểm duyệt.
- **c. Implementation hiện tại**: Dùng Static Orchestrator bọc lấy các module bằng Interface (Dependency Injection).
- **d. Phát triển Production**: Triển khai FastAPI Dependency Injection và gắn OpenTelemetry trace log.
- **e. Trade-offs**: *Perf*: Nhanh. *Complexity*: Setup DI hơi phức tạp nhưng luồng chạy rõ ràng. *Testability*: Tuyệt hảo.
- **f. Ảnh hưởng chất lượng**: An toàn 100%, không bao giờ bị trượt luồng xử lý (skip step).
- **g. References**: ADR-301.

### 3.2. Query Rewriting Strategy
- **a. Lý thuyết chuẩn**: LLM Query Rewriting + HyDE.
- **b. Alternatives Considered**: 
  - *Không làm gì*: Hỏng kết quả tìm kiếm.
- **c. Implementation hiện tại**: Rule-based Regex Filter (Chỉ xóa chữ "cho tôi hỏi").
- **d. Phát triển Production**: Cắm API LLM loại nhỏ (GPT-4o-mini) làm Standalone Query Rewriter, nạp kèm History hội thoại. Thêm Redis Cache.
- **e. Trade-offs**: *Perf*: Chậm hơn 1s. *Cost*: Tốn API. *Extensibility*: Cực cao.
- **f. Ảnh hưởng chất lượng**: Bản Dev đang bị mù bối cảnh (nếu hỏi câu nối tiếp "thế còn điều 2", hệ thống không hiểu).
- **g. References**: ADR-302.

### 3.3. Reranking & Filtering Strategy
- **a. Lý thuyết chuẩn**: Cross-Encoder Model.
- **b. Alternatives Considered**: 
  - *Chỉ xài Cross-Encoder*: Model có thể lỡ đưa văn bản cũ lên top 1.
- **c. Implementation hiện tại**: `MockReranker` (Chỉ filter, không chấm điểm) hoặc `RuleBasedReranker` (Jaccard).
- **d. Phát triển Production**: BGE-Reranker trên GPU, bắt buộc chạy qua hàm `_hard_filter` để vứt văn bản "hết_hiệu_lực" trước khi Rerank AI.
- **e. Trade-offs**: *Memory*: Tốn VRAM. *Latency*: Tăng 100ms.
- **f. Ảnh hưởng chất lượng**: Bản Dev Rerank không hiệu quả, dẫn đến LLM đôi khi nhận Context sai lệch.
- **g. References**: ADR-303.

### 3.4. Verification Pipeline (Chống ảo giác)
- **a. Lý thuyết chuẩn**: NLI Model (Natural Language Inference) Entailment Checker.
- **b. Alternatives Considered**: 
  - *LLM-as-a-judge*: Đắt, chậm, dễ bị lươn lẹo.
  - *Regex check*: Nhanh nhưng không kiểm tra được ngữ nghĩa.
- **c. Implementation hiện tại**: `MockGroundednessVerifier` quét chữ "ảo giác" giả lập lỗi, và Regex Citation cơ bản.
- **d. Phát triển Production**: Dựng NLI Model (PhoBERT NLI) chấm điểm Entailment từng câu của LLM so với Context.
- **e. Trade-offs**: *Perf*: Chậm thêm 200ms. *Safety*: An toàn tuyệt đối.
- **f. Ảnh hưởng chất lượng**: Bản Dev đang tin tưởng mù quáng vào kết quả sinh ra, dễ bị ảo giác pháp lý nghiêm trọng.
- **g. References**: ADR-304.

## 4. Những điểm khác so với kế hoạch kiến trúc ban đầu
- **Không dùng Semantic Router**: Thay vì để LLM tự quyết định phân loại intent (Hỏi Luật vs ChitChat), toàn bộ câu hỏi đều bị ép đi qua DB tìm kiếm luật. (Do thiếu Agent).
- **LLM Generator Mock**: Đang trả về Text fix cứng, chưa tích hợp gọi LLM thật qua thư viện `google-genai` hoặc `openai`.

## 5. Chiến lược Phần cứng & GPU (GPU Strategy)
Kiến trúc sư thiết kế hạ tầng Production cho Module 3 cần cấp phát GPU như sau:
- **Tầng Orchestrator / Prompt Builder (CPU)**: Rất nhẹ, chạy thuần Code Logic Python. Không cần GPU.
- **Tầng Reranker (Cross-Encoder)**: Yêu cầu tính toán nặng. Bắt buộc **1x GPU NVIDIA T4 (16GB VRAM)** để model `bge-reranker` tính toán ma trận Attention kịp thời gian thực (< 100ms).
- **Tầng Generator (LLM)**: Nếu gọi API Cloud thì không tốn GPU. Nếu **Self-hosted LLM** (Bảo mật On-premise, mô hình <= 4B), bắt buộc **1x GPU NVIDIA T4 (16GB VRAM)** (tuyệt đối không dùng mô hình >= 7B để tuân thủ kiến trúc).
- **Tầng Verifier (NLI Model)**: Cần thêm **1x GPU NVIDIA T4 (16GB VRAM)** chạy riêng rẽ Microservice để không chặn luồng Reranker.

## 6. Production Roadmap
1. **Bước 1 (Dependency Injection & LLM)**: 
   - *Hành động*: Setup FastAPI DI Container. Thay `MockLLMGenerator` bằng API thật (`GeminiGenerator`). Bổ sung Streaming Response.
   - *Điều kiện hoàn thành*: Hệ thống trả về câu trả lời trôi chảy từ LLM dựa trên Context được nhúng thật sự.
2. **Bước 2 (Deploy Reranker)**: 
   - *Hành động*: Tách lớp Inference Reranker sang TEI. Viết HTTP Client trong code.
   - *Điều kiện hoàn thành*: Top 5 Context được đẩy cho LLM không chứa văn bản hết hiệu lực và cực kỳ sát câu hỏi.
3. **Bước 3 (NLI Verification)**: 
   - *Hành động*: Deploy model NLI. Tích hợp `NLIGroundednessVerifier`.
   - *Điều kiện hoàn thành*: Hệ thống tự động từ chối trả lời hoặc chặn response khi LLM lỡ sinh ra câu láo.

## 7. Impact Analysis toàn hệ thống
- Bất kỳ nâng cấp nhỏ nào trong Module 3 (như đổi Prompt) sẽ **tác động trực tiếp ngay lập tức** tới chất lượng câu trả lời cuối cùng của User mà không cần làm lại Index. Module 3 là bộ mặt của hệ thống, đòi hỏi Test E2E khắt khe nhất.

## 8. Risks & Technical Debt tổng hợp
- **Rủi ro**: 
  - Token Limit: Nguy cơ LLM Context Window bị tràn nếu lấy Chunk quá to mà không cấu hình kỹ `ContextWindowManager`.
  - Độ trễ (Latency) dồn toa. Nếu dùng toàn API ngoài, Module 3 sẽ mất 5-7 giây mới trả lời được User, gây ức chế.
- **Tech Debt**: 
  - Regex CitationVerifier rất khó bảo trì với chuẩn trích dẫn tiếng Việt phức tạp (điểm a, khoản 1, điều 2...).
  - Thiết kế Error Boundary chưa hoàn thiện, lỗi ở khâu Retriever có thể làm văng lỗi (500) toàn pipeline thay vì fallback an toàn.

## 9. Migration Guide (Cho các bước Roadmap)
- **Dependency Injection**: Xóa lệnh khởi tạo thủ công trong `demo.py`, bọc toàn bộ thành Dependency Providers. Không ảnh hưởng luồng code chính.
- **Reranker & Verifier**: Khi cắm Service thật qua HTTP, bắt buộc thiết lập cơ chế `Timeout` và `Fallback`. Tránh trường hợp NLI Server chết khiến App đứng im mãi mãi. Nếu Timeout, kích hoạt cờ cảnh báo rủi ro (Warning) nhưng vẫn cho qua (Hoặc tùy rule an toàn của doanh nghiệp).
