# ADR 303: Chiến lược Reranking và Rule-based Filtering

## 1. Context
Sau khi truy vấn (Retrieval) Hybrid trả về top 30 ứng viên (Chunks). Danh sách này là kết quả trộn lẫn bằng thuật toán RRF. Dù vậy, điểm số này chỉ tính toán độc lập từng chunk so với câu hỏi (Bi-Encoder). Để tăng độ chính xác lên cực đại, ta cần đánh giá lại từng cặp (Câu hỏi - Chunk) một cách trực tiếp. 

Hơn nữa, trong hệ thống pháp luật, một văn bản có thể rất khớp với câu hỏi nhưng đã HẾT HIỆU LỰC, thì nó là rác.

## 2. Problem Statement
**Làm sao để sắp xếp lại (Rerank) các ứng viên chính xác nhất và áp dụng luật loại trừ văn bản "Hết hiệu lực"?**
Giao phó toàn bộ việc đánh giá "hiệu lực văn bản" cho mô hình Rerank AI tự học là cực kỳ nguy hiểm (nó có thể vô tình chấm điểm cao cho một văn bản đã hết hạn chỉ vì nội dung quá khớp).

## 3. Alternatives Considered

**Option A: Chỉ dùng Cross-Encoder AI**
- **Nhược điểm**: Rủi ro cao về mặt pháp lý nếu model lỡ đưa văn bản cũ lên Top 1 (vì AI Reranker thường bỏ qua meta data nhỏ như status).

**Option B: Chỉ lọc bằng Rule (Metadata Filter)**
- **Nhược điểm**: Lọc được văn bản cũ, nhưng không cải thiện được thứ tự sắp xếp ngữ nghĩa của những văn bản còn lại.

**Option C: Rule-based Filtering trước, sau đó Reranking bằng Cross-Encoder**
- **Ưu điểm**: Đảm bảo 100% tuân thủ pháp lý (loại thẳng tay các chunk có metadata `trang_thai == "hết_hiệu_lực"`). Phần còn lại (văn bản hợp lệ) mới giao cho AI Reranker sắp xếp lại bằng cách chấm điểm theo cặp.

## 4. Decision
Quyết định: **Chọn Option C**.
Mọi class triển khai `BaseReranker` BẮT BUỘC phải thực hiện bước `_hard_filter()` các metadata không hợp lệ (như `hết_hiệu_lực`) trước khi chấm điểm Rerank. Pipeline: `Top 30 -> Filter -> Top N hợp lệ -> AI Rerank -> Top 5`.

## 5. Trade-offs (8 Trục)
- **Performance**: Cross-Encoder chấm điểm theo cặp rất chậm (O(N) thay vì O(1)). Việc thêm bước Filter trước giúp loại bớt một lượng rác đáng kể, giảm tải cho GPU khi Rerank.
- **Memory**: Tốn VRAM khoảng 4-8GB để load mô hình Cross-Encoder.
- **Latency**: Tăng khoảng 50-100ms cho việc chạy AI Reranking.
- **Cost**: Tốn kém phí vận hành Server GPU cho inference Reranker.
- **Complexity**: Tăng thêm một Model AI phải duy trì trong hệ thống, cấu hình pipeline phức tạp hơn.
- **Extensibility**: Có thể dễ dàng thay thế mô hình Rerank tốt hơn trong tương lai mà không ảnh hưởng luồng Filter.
- **Maintainability**: Đưa luật pháp lý (Hard Rule) vào trong Reranker đòi hỏi kỹ sư phải rất cẩn thận khi cập nhật. Lẽ ra Filter nên nằm ở Qdrant, nhưng hiện Qdrant In-memory chưa làm triệt để được, nên nhét vào Reranker làm lá chắn cuối cùng.
- **Testability**: Dễ viết Unit test để kiểm tra mô hình có vứt đúng văn bản cũ đi không.

## 6. Current Implementation
- **Trạng thái**: Đang sử dụng `MockReranker` (Chỉ filter, không chấm điểm) và `RuleBasedReranker` (Chấm điểm bằng độ trùm từ vựng Jaccard Overlap).
- **Giới hạn**: Chưa có CrossEncoder chạy thật, nên điểm số Rerank thực tế khá lộn xộn.
- **Ảnh hưởng**: Không chứng minh được sức mạnh thực sự của hệ thống AI, chỉ đảm bảo được việc chặn văn bản hết hiệu lực.

## 7. Production Architecture
- Sử dụng mô hình chuyên dụng `BAAI/bge-reranker-v2-m3`. Triển khai độc lập qua **vLLM** hoặc **TEI (Text Embeddings Inference)** để tăng tốc độ phản hồi trên GPU, gọi qua REST API.

## 8. Migration Guide
- **Thay component nào**: Khởi tạo class `CrossEncoderReranker` (Gọi API hoặc load cục bộ HuggingFace). Thay cho bản Mock hiện tại.
- **Sửa file nào**: `module3/reranker.py`. Cập nhật dependency list.
- **Rollback strategy**: Nếu API Reranker Server quá tải/chết, fallback ngay lập tức về `MockReranker` (Chỉ Filter lấy nguyên thứ tự RRF cũ) để không gián đoạn dịch vụ.

## 9. Impact Analysis
- Tăng cực mạnh chỉ số Precision@5 (Top 5 ngữ cảnh được nạp vào phần Context Window của LLM Generator sẽ là những đoạn chính xác tuyệt đối, bám rất sát câu hỏi). Điều này quyết định 80% độ thông minh của LLM ở các bước sau.

## 10. Risks & Technical Debt
- **Rủi ro**: 
  - Cross-Encoder giới hạn input token khoảng 512. Nếu ghép câu hỏi + Chunk dài quá 512 token, model bị cụt chữ, chấm sai.
- **Technical Debt**: Việc đặt Hard Rule (`hết_hiệu_lực`) bên trong class `Reranker` vi phạm nguyên lý Single Responsibility (Lẽ ra nó chỉ làm nhiệm vụ chấm điểm). Nhưng do Shortcut hệ thống, đành chấp nhận.

## 11. Future Roadmap
1. Simulation (Hiện tại): Mock / Jaccard Overlap.
2. Production: BGE-Reranker trên GPU qua TEI + Cứng nhắc Rule lọc trạng thái.
3. Enterprise: Fine-tune mô hình BGE-Reranker trên Dataset câu hỏi pháp lý Việt Nam, vì model BGE-M3 gốc chấm văn bản tiếng Việt vẫn hơi "ngố" ở các từ vựng pháp lý hẹp.

## 12. References
- [Cross-Encoder Models (Sentence Transformers)](#)
- [BGE Reranker v2 (HuggingFace)](#)
