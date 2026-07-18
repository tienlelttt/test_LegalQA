# ADR 302: Chiến lược Hiểu câu hỏi (Query Normalization & LLM Rewriter)

## 1. Context
Người dùng thường đặt câu hỏi rất "khẩu ngữ", viết tắt, hoặc thiếu chủ ngữ (Ví dụ: "cho mình hỏi luật đđ năm 24 có điểm gì mới?"). Đưa nguyên câu hỏi thô này vào Vector Database sẽ cho ra kết quả cực kỳ kém vì Vector bị nhiễu bởi các từ "cho mình hỏi". Hơn nữa, trong hội thoại đa lượt, người dùng có thể hỏi "thế còn điều 5 thì sao?", hệ thống cần bối cảnh để hiểu "điều 5" của văn bản nào.

## 2. Problem Statement
**Làm sao để làm sạch và "viết lại" (rewrite) câu hỏi thô thành một câu truy vấn chuẩn mực (Query) mà Vector Database có thể hiểu chính xác nhất?**

## 3. Alternatives Considered

**Option A: Không xử lý gì cả (Raw Query)**
- **Nhược điểm**: Recall cực thấp, search sai tè le nếu user gõ sai chính tả hoặc dùng khẩu ngữ.

**Option B: Rule-based Normalizer + Keyword Extraction**
- **Ưu điểm**: Nhanh, loại bỏ được các stop-words như "cho hỏi".
- **Nhược điểm**: Không giải quyết được các từ viết tắt chuyên ngành lạ, hoặc không xử lý được vấn đề đại từ nhân xưng (Co-reference resolution) trong hội thoại đa lượt.

**Option C: LLM Query Rewriting + HyDE (Hypothetical Document Embeddings)**
- **Ưu điểm**: Khả năng diễn đạt lại hoàn hảo. Có thể suy diễn ý định và mở rộng ngữ nghĩa, độ chính xác tăng vượt bậc (đặc biệt trong hội thoại).
- **Nhược điểm**: Tốn kém phí API, chậm chạp (phải chờ sinh text).

## 4. Decision
Quyết định: **Áp dụng chiến lược Hỗn hợp (Hybrid)**. 
Xây dựng pipeline 2 bước tuần tự:
1. `QueryNormalizer`: Sửa unicode, xóa khoảng trắng thừa, mở rộng từ viết tắt phổ biến (nhanh, chi phí 0).
2. `QueryRewriterInterface`: Ở MVP dùng Rule-based (Regex), ở Production bắt buộc phải dùng LLM để viết lại câu hỏi đơn lẻ (Standalone Query).

## 5. Trade-offs (8 Trục)
- **Performance**: Chậm. Chờ LLM viết lại câu hỏi mất khoảng 0.5 - 1 giây.
- **Memory**: Rất nhỏ.
- **Latency**: Tăng thêm độ trễ cho toàn bộ hệ thống ngay ở bước đầu tiên.
- **Cost**: Tốn chi phí API LLM (dù có thể dùng model rẻ như Gemini Flash hoặc GPT-4o-mini).
- **Complexity**: Tăng độ phức tạp ở bước xử lý hội thoại (phải nạp đủ history vào prompt rewriter).
- **Extensibility**: Mở ra hướng dùng Multi-Query (sinh 3 phiên bản câu hỏi khác nhau để tìm kiếm tăng Recall).
- **Maintainability**: Dễ bảo trì, chỉ cần update prompt của LLM.
- **Testability**: Dễ test bằng các tập Dataset câu hỏi phức tạp.

## 6. Current Implementation
- **Trạng thái**: Đang dùng `QueryNormalizer` và `RuleBasedQueryRewriter` (Lọc thủ công bằng Regex các từ "cho tôi hỏi", "quy định sao").
- **Giới hạn**: Không hiểu được bối cảnh hội thoại (History). Không biết "đđ" là "Đất đai".
- **Ảnh hưởng**: Chấp nhận được với môi trường Dev thử nghiệm trên những câu hỏi gõ chuẩn.

## 7. Production Architecture
- Kích hoạt `LLMQueryRewriter`: Gọi API GPT-4o-mini hoặc Gemini Flash. Prompt sẽ nhận vào `Lịch sử hội thoại` + `Câu hỏi hiện tại` để sinh ra 1 câu truy vấn độc lập duy nhất (Standalone Query).
- Hệ thống Redis Cache: Caching lại các cặp `(Query thô -> Query đã rewrite)` để tránh gọi LLM 2 lần cho cùng 1 câu hỏi phổ biến.

## 8. Migration Guide
- **Thay component nào**: Thay thế `RuleBasedQueryRewriter` bằng `LLMQueryRewriter` trong hàm khởi tạo của `QueryOrchestrator`.
- **Sửa file nào**: Triển khai logic gọi API thật vào trong class `LLMQueryRewriter` tại `module3/query_understanding.py`.
- **Pipeline thay đổi**: Không phá vỡ kiến trúc cũ.

## 9. Impact Analysis
- **Chapter 2 (Retrieval)**: Module 2 sẽ nhận được 1 câu truy vấn chất lượng, sạch sẽ và chứa các từ khóa chuẩn xác, làm cho Sparse Search (BM25) bắt dính ngay lập tức.

## 10. Risks & Technical Debt
- **Rủi ro**: LLM viết lại sai ý định (Intent) của người dùng. Cần prompt rất cẩn thận và có fallback. Ví dụ: user hỏi "Luật Đất đai", LLM lại rewrite thành "Luật Đất đại".
- **Technical Debt**: Hiện tại chưa lưu log các câu hỏi thô để làm dataset tinh chỉnh model.

## 11. Future Roadmap
1. Simulation (Hiện tại): Rule-based Rewriting.
2. Production: LLM Standalone Query Rewriting + Redis Cache.
3. Enterprise: Multi-Query Generation + DSPy (Tự động tối ưu Prompt Rewrite bằng Machine Learning).

## 12. References
- [Query Rewriting for Conversational AI](#)
- [HyDE: Precise Zero-Shot Dense Retrieval without Relevance Labels](#)
