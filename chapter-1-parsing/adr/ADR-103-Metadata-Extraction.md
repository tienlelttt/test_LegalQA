# ADR 103: Chiến lược trích xuất siêu dữ liệu (Metadata Extraction Strategy)

## 1. Context
Trong hệ thống LegalQA, tìm kiếm dựa trên Vector đơn thuần (Dense Search) là không đủ. Luật pháp yêu cầu tìm kiếm có điều kiện nghiêm ngặt (chỉ tìm trong văn bản "còn hiệu lực", hoặc tìm đích danh "Nghị định 15"). Metadata extraction là bắt buộc để hỗ trợ quá trình Filtering ở Query Pipeline.

## 2. Problem Statement
**Làm sao để trích xuất được số hiệu văn bản, ngày ban hành, tình trạng hiệu lực và các văn bản bị thay thế (Citations)?**
Việc trích xuất số Điều, Khoản khá dễ qua Regex, nhưng việc xác định tình trạng hiệu lực hoặc quan hệ thay thế cần sự hiểu biết ngôn ngữ phức tạp.

## 3. Alternatives Considered

**Option A: Rule-based (Regex/Entity Extraction NLP)**
- **Ưu điểm**: Cực kỳ nhanh, độ trễ bằng không. Chính xác tuyệt đối cho các format cố định (số hiệu: "NĐ-CP").
- **Nhược điểm**: Bất lực hoàn toàn trước diễn đạt tự do. Ví dụ: "Nghị định này thay thế Nghị định X và bãi bỏ các khoản 1, 2, 3 Điều 4 của Luật Y". Cấu trúc này vô hạn, không thể dùng Regex bắt hết.
- **Vì sao không chọn**: Không đảm bảo được Extraction cho Citation Graph.

**Option B: Dùng LLM cho toàn bộ văn bản (LLM for everything)**
- **Ưu điểm**: Trích xuất hoàn hảo mọi quan hệ phức tạp ở bất kỳ đâu trong file.
- **Nhược điểm**: Tốn kém vô cùng. Một cuốn luật dài 100 trang ném vào LLM sẽ tiêu tốn hàng trăm ngàn token cho mỗi file. Tốc độ parse file giảm xuống còn vài chục phút/file.
- **Vì sao không chọn**: Lãng phí tài nguyên không đáng có vì thông tin hiệu lực thường chỉ nằm ở Chương cuối cùng.

**Option C: Hybrid (Regex cho định dạng chuẩn + LLM cho các đoạn mở/kết)**
- **Ưu điểm**: Tối ưu tuyệt đối tốc độ (Regex lấy số hiệu, cơ quan ban hành). Chỉ dùng LLM phân tích đoạn "Căn cứ" (đầu file) và "Điều khoản thi hành" (cuối file) - nơi chứa 99% thông tin hiệu lực/sửa đổi.
- **Nhược điểm**: Cần thiết kế Pipeline linh hoạt kết hợp cả hai, có khả năng bóc 2000 từ đầu và 2000 từ cuối.

## 4. Decision
Quyết định: **Chọn Option C (Hybrid Strategy)**.
Sử dụng LLM trích xuất siêu dữ liệu nhưng **giới hạn phạm vi**. Chỉ cung cấp cho LLM vài trang đầu và vài trang cuối của văn bản để tiết kiệm chi phí và tăng độ chính xác. Bắt LLM trả về cấu trúc JSON (Structured Output).

## 5. Trade-offs (8 Trục)
- **Performance**: Chậm hơn so với Regex thuần, nhưng nhanh hơn Option B hàng nghìn lần.
- **Memory**: Rất ít ảnh hưởng nếu gọi API. Nếu dùng Self-hosted LLM (ví dụ <= 4B model), tốn khoảng 8-16GB VRAM hệ thống.
- **Latency**: Tăng thời gian Ingestion thêm 2-3 giây cho mỗi văn bản do phải chờ API LLM trả kết quả. Nhưng Ingestion là Offline process nên chấp nhận được.
- **Cost**: Tốn một lượng nhỏ chi phí API LLM cho mỗi văn bản (vài cent). Rất rẻ so với Option B.
- **Complexity**: Phức tạp do cần cấu hình Pydantic JSON Validator, quản lý connection API, và xử lý Rate Limit.
- **Extensibility**: Rất dễ thêm các Entity cần trích xuất mới (chỉ việc sửa Prompt).
- **Maintainability**: Khá khó do phụ thuộc vào bên thứ 3 (OpenAI/Google). Nếu họ đổi API, hệ thống phải cập nhật theo.
- **Testability**: Cần mock API LLM để chạy test. Dễ xảy ra flaky test nếu không có JSON schema strict.

## 6. Current Implementation
- **Trạng thái**: Simulation Layer (`MockLLMMetadataExtractor` trong `src/extractor.py`).
- **Giới hạn**: Đang trả về dữ liệu hardcode (Mock), chưa cắm API thật để gọi Gemini/OpenAI. Hoàn toàn "mù" trước dữ liệu thực.
- **Ảnh hưởng**: Phục vụ tốt cho việc xây dựng kiến trúc và Test ở Local (Pass 100% test flow), nhưng chưa có giá trị thực tiễn với file PDF mới.

## 7. Production Architecture
- Implement `LLMMetadataExtractor` sử dụng `pydantic` để validate JSON trả về từ API `Gemini-1.5-Flash` (hoặc GPT-4o-mini).
- Prompt thiết kế chuyên biệt cho Domain Pháp lý Việt Nam (System Prompt: "Bạn là chuyên gia pháp lý...").
- Cơ chế Queue (hàng đợi) cho việc gọi API để tránh bị Rate Limit.

## 8. Migration Guide
- **Thay component nào**: Xóa/giữ `MockLLMMetadataExtractor` làm mock test. Triển khai class mới kế thừa `MetadataExtractorInterface`.
- **Sửa file nào**: `src/extractor.py` (cắm API key và gọi LLM client).
- **Pipeline thay đổi**: Không thay đổi (Module 2 vẫn nhận Chunk với Metadata đi kèm).
- **Dữ liệu**: Nếu đổi từ Mock sang API thật, bắt buộc chạy Ingestion Pipeline lại từ đầu để lấy metadata thật.
- **Backward compatibility**: Interface `extract_metadata` không đổi (trả về JSON Dict).
- **Rollback strategy**: Nếu API sập/hết tiền, fallback về `RegexMetadataExtractor` (chỉ lấy số hiệu và tên, bỏ trống tình trạng hiệu lực).

## 9. Impact Analysis
- **Chapter 2 (Vector DB)**: Metadata thực tế (ngày hiệu lực, loại văn bản) cho phép tạo HNSW Index có Payload Filter tối ưu hơn, tránh tình trạng Hard-filter loại nhầm văn bản hợp lệ.
- **Chapter 2 (Graph)**: Citations (văn bản sửa đổi/thay thế) cung cấp input trực tiếp để xây dựng Knowledge Graph.

## 10. Risks & Technical Debt
- **Rủi ro**: 
  - LLM sinh ảo giác (bịa ra tên văn bản sửa đổi không có thật).
  - LLM trả về JSON sai format khiến Pydantic vỡ trận.
- **Technical Debt**: Cần implement cơ chế Retry (ví dụ dùng thư viện `Tenacity`) để bắt các lỗi API timeout hoặc JSON parsing. Hiện tại chưa có.

## 11. Future Roadmap
1. Simulation (Hiện tại): Mock data.
2. Production: Tích hợp LLM API (Gemini/OpenAI) + Pydantic JSON Validator + Tenacity Retry.
3. Enterprise: Tự host model nhỏ (<= 4B) chuyên tinh chỉnh (fine-tune) cho tác vụ Entity Extraction của luật Việt Nam để đảm bảo bảo mật dữ liệu tuyệt đối (Data Privacy) và tiết kiệm chi phí dài hạn.

## 12. References
- [Structured Output with LLMs (OpenAI Docs)](#)
- [Hybrid Metadata Extraction Best Practices](#)
