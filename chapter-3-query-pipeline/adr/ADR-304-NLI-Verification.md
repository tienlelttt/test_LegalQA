# ADR 304: Hệ thống Kiểm chứng Chống ảo giác (Verification Pipeline & NLI)

## 1. Context
Trong LegalQA, "Trả lời sai" là kết quả tồi tệ hơn rất nhiều so với "Từ chối trả lời". Nếu LLM sinh ra một câu trả lời (Ảo giác - Hallucination) không hề có trong ngữ cảnh (Context), hệ thống sẽ đối mặt với rủi ro pháp lý nghiêm trọng. Bắt buộc phải có một lớp lưới lọc chặn lại trước khi câu trả lời tới tay End-user.

## 2. Problem Statement
**Làm sao để bắt và chặn đứng câu trả lời bị ảo giác trước khi trả về cho người dùng?**

## 3. Alternatives Considered

**Option A: LLM-as-a-judge (Dùng chính LLM để kiểm tra lại)**
- **Ưu điểm**: Linh hoạt, dễ làm. Prompt: "Câu trả lời này có nằm trong ngữ cảnh không?".
- **Nhược điểm**: Tốn chi phí x2 (gọi API 2 lần). Chậm (phải đợi LLM sinh text giải thích). LLM judge đôi khi cũng tự huyễn hoặc và đánh giá sai chính nó.
- **Vì sao không chọn**: Chi phí và latency quá cao cho Production.

**Option B: Regex & Keyword Check**
- **Ưu điểm**: Nhanh vô song (0ms độ trễ).
- **Nhược điểm**: Chỉ kiểm tra được format Citation bề mặt. Không thể biết ngữ nghĩa của câu trả lời có "bịa" thêm nội dung hay không. Ví dụ LLM trả lời "Luật cho phép X" trong khi luật cấm X, Regex không bắt được.

**Option C: Pipeline kết hợp (Regex Format + NLI Groundedness)**
- **Ưu điểm**: Chia thành nhiều chốt chặn tuần tự (`Verifiers`). `CitationVerifier` dùng Regex để bắt lỗi trích dẫn. `NLIGroundednessVerifier` dùng mô hình NLI (Natural Language Inference) chuyên dụng cỡ nhỏ để đánh giá độ "Entailment" (Suy diễn logic) xem từng câu của Answer có được Context "bao hàm" không. Mô hình NLI rẻ, nhẹ và nhanh hơn LLM Generative rất nhiều.

## 4. Decision
Quyết định: **Chọn Option C (Verification Pipeline)**.
- Xây dựng một Pipeline tuần tự. Lấy Answer từ LLM đi qua từng chốt chặn. Nếu rớt ở bất kỳ chốt nào (vd: Mismatch citation, Contradiction NLI), cờ `is_grounded` sẽ bị đánh `False` và hệ thống trả về thông báo lỗi an toàn (ví dụ: "Không đủ thông tin").

## 5. Trade-offs (8 Trục)
- **Performance**: Việc kiểm tra NLI cho từng câu đơn của Answer tốn một chút overhead để phân tách (Tokenize sentences) và chạy GPU.
- **Memory**: Mô hình NLI (như DeBERTa) cỡ vừa, tốn khoảng 2-4GB VRAM.
- **Latency**: Tốn thêm thời gian chạy NLI model (khoảng 100-200ms) trước khi trả về kết quả cuối.
- **Cost**: Cần cấp một lượng tài nguyên GPU nhỏ liên tục cho NLI server.
- **Complexity**: Việc mapping các câu của Answer về các câu của Context để check NLI khá phức tạp.
- **Extensibility**: Có thể cắm thêm vô hạn các loại `Verifier` khác (ví dụ: Profanity Filter, Toxic Filter, PII Filter).
- **Maintainability**: Các rule Regex của CitationVerifier cần cập nhật thường xuyên.
- **Testability**: Dễ test bằng các tập dữ liệu có sẵn (Tạo file JSON chứa câu Grounded và câu Hallucinated để test tự động).

## 6. Current Implementation
- **Trạng thái**: Đã có kiến trúc `VerificationPipeline` và `CitationVerifier` (Regex cơ bản). Đang dùng `MockGroundednessVerifier` (Chỉ dùng rule chữ, quét xem có từ "tuyệt đối" / "ảo giác" không để giả lập lỗi).
- **Giới hạn**: Chưa có logic NLI thật sự. `CitationVerifier` regex còn thô (khó bắt được format chứa Điểm, Khoản lồng nhau).
- **Ảnh hưởng**: Hệ thống hiện tại hoàn toàn "mù" trước ảo giác sinh ra từ AI. 

## 7. Production Architecture
- Viết `NLIGroundednessVerifier` kế thừa `BaseVerifier`.
- Deploy mô hình NLI tiếng Việt (như `vinai/phobert-base-v2` fine-tune cho tác vụ NLI) lên HuggingFace TEI hoặc Triton.
- Gọi API để chấm điểm `Entailment / Contradiction / Neutral`. Nếu phát hiện `Contradiction` hoặc `Neutral`, hệ thống sẽ trả về câu trả lời mặc định an toàn.

## 8. Migration Guide
- **Thay component nào**: Xóa `MockGroundednessVerifier`. Thêm cấu hình Inject `NLIGroundednessVerifier` vào Pipeline.
- **Sửa file nào**: Cập nhật logic call HTTP bên trong `module3/verifier.py`.
- **Pipeline thay đổi**: Không phá vỡ luồng chính.
- **Rollback strategy**: Nếu NLI Server quá tải, fallback cờ `is_grounded = True` để hệ thống không bị đứng, nhưng kích hoạt cảnh báo đỏ trên Monitoring.

## 9. Impact Analysis
- Hệ thống sẽ an toàn tuyệt đối về mặt pháp lý. Đánh đổi lại, tỷ lệ "Từ chối trả lời" sẽ tăng vọt (False Negative) do NLI model đôi khi đánh giá quá khắt khe. Trải nghiệm người dùng (UX) có thể bị giảm (user hỏi nhiều câu nhưng app không dám trả lời).

## 10. Risks & Technical Debt
- **Rủi ro**: Mô hình NLI Tiếng Việt chất lượng cao khá hiếm, model có sẵn trên mạng chưa chắc hiểu được từ lóng pháp lý, có thể cần tự Fine-tune.
- **Technical Debt**: Việc tách câu (Sentence Tokenization) tiếng Việt đang dùng thư viện chuẩn, đôi khi tách sai ở các chữ viết tắt ("VD.").

## 11. Future Roadmap
1. Simulation (Hiện tại): Mock/Regex Pipeline.
2. Production: NLI Model Entailment.
3. Enterprise: Tự động xóa (Auto-redact) phần nội dung bị ảo giác và chỉ trả về phần nội dung an toàn thay vì block toàn bộ câu trả lời.

## 12. References
- [Evaluating RAG Systems with RAGAS (Faithfulness/Groundedness metric)](#)
- [Self-Check NLI for Hallucination Detection](#)
