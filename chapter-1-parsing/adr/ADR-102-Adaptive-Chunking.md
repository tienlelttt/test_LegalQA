# ADR 102: Chiến lược phân mảnh ngữ nghĩa (Adaptive Hierarchical Chunking vs Fixed-size Chunking)

## 1. Context
Sau khi Parser tạo ra cây cấu trúc pháp lý, dữ liệu cần được chia nhỏ (Chunk) để Vector Database có thể mã hóa (Embed) hiệu quả, vì các mô hình Embedding (như BGE-M3 hay MiniLM) có giới hạn độ dài context window (ví dụ: 512, 1024, 8192 token).

## 2. Problem Statement
**Làm thế nào để chia văn bản thành các Chunk vừa đủ nhỏ cho mô hình Embedding, nhưng không làm đứt gãy ngữ cảnh pháp lý (như Điều kiện áp dụng, ngoại lệ nằm ở Khoản khác)?**
Nếu chia cố định (ví dụ 512 tokens), câu văn sẽ bị cắt ngang, khiến LLM nhận được thông tin không trọn vẹn và suy diễn sai.

## 3. Alternatives Considered

**Option A: Fixed-size Chunking (Naive text split)**
- **Ưu điểm**: Dễ cài đặt (dùng LangChain `RecursiveCharacterTextSplitter`), phổ biến, chạy nhanh.
- **Nhược điểm**: Phá vỡ hoàn toàn ngữ cảnh pháp lý. Điểm a) có thể bị cắt làm đôi, dẫn đến câu trả lời thiếu điều kiện áp dụng. Khó mapping ngược lại văn bản gốc.
- **Vì sao không chọn**: Legal domain yêu cầu tính toàn vẹn câu chữ, việc cắt ngang một Khoản luật là không thể chấp nhận được.

**Option B: Document-level Embedding**
- **Ưu điểm**: Giữ trọn bối cảnh 100%. Không mất công đoạn Chunking.
- **Nhược điểm**: 
  - Vượt quá max token limit của mô hình nhúng (thường các model nhúng chỉ max 8192).
  - Tìm kiếm (Retrieval) kém chính xác vì context quá rộng, cosine similarity bị loãng.
- **Vì sao không chọn**: Không khả thi về mặt kỹ thuật cho Semantic Search hiện tại.

**Option C: Adaptive Hierarchical Chunking (Parent-Child Strategy)**
- **Ưu điểm**: Đảm bảo toàn vẹn ngữ nghĩa. Cố gắng lấy "Điều" làm đơn vị chuẩn. Nếu quá dài, chẻ nhỏ thành "Khoản" (Child Chunk), nhưng tự động dán (prepend) tiêu đề Điều vào mỗi Khoản.
- **Nhược điểm**: Code phức tạp hơn, tốn chi phí lưu trữ các đoạn Text lặp (tiêu đề Điều).

## 4. Decision
Quyết định: **Chọn Option C (Adaptive Hierarchical Chunking)**.
- **Kiến trúc**: Sử dụng "Điều" (Article) làm ranh giới ngữ nghĩa. Nếu Điều dưới 512 tokens, giữ nguyên. Nếu vượt, phân rã thành các Khoản. Mỗi Child Chunk (Khoản) sẽ mang theo thông tin ngữ cảnh của Parent (Điều).

## 5. Trade-offs (8 Trục)
- **Performance**: Nhanh, tuy nhiên tốn overhead nhỏ để duyệt đệ quy (recursive check token length).
- **Memory**: Tốn thêm khoảng 10-15% RAM và dung lượng lưu trữ so với thông thường do lặp lại Prefix (chuỗi "Điều X:...") ở các Child chunks.
- **Latency**: Xử lý Offline (Ingestion) nên latency không quan trọng.
- **Cost**: Không tốn chi phí bên ngoài.
- **Complexity**: Mức độ phức tạp trung bình. Cần quản lý cấu trúc đệ quy (Recursive Chunking).
- **Extensibility**: Tuyệt vời. Rất dễ mở rộng sang cơ chế **Parent-Child Retrieval** thực thụ (Tìm kiếm child, nhưng lấy ID để fetch toàn bộ Parent document đưa cho LLM).
- **Maintainability**: Dễ bảo trì, logic chia cắt rõ ràng theo Pydantic tree.
- **Testability**: Dễ test bằng cách truyền vào một cây giả và assert kích thước các mảnh vỡ (Chunks).

## 6. Current Implementation
- **Trạng thái**: Đã implement (trong `src/chunker.py`).
- **Giới hạn**: Chỉ xử lý đệ quy xuống cấp "Điểm". Chưa có logic trượt ngữ cảnh (sliding window) cho những "Điểm" siêu dài (sliding window cực hiếm gặp trong luật nhưng vẫn có thể xảy ra).
- **Ảnh hưởng**: Đáp ứng được 99% văn bản luật hiện hành. 

## 7. Production Architecture
- Sử dụng Data Pipeline bất đồng bộ (Async Ingestion) để xử lý Chunking qua Celery/RabbitMQ.
- Thay vì dán cứng Prefix (Prepend), sử dụng cơ chế **Parent-Child Mapping**:
  - Lưu `Child Chunk` vào Qdrant để embed và search.
  - Lưu `Parent Document` vào Document Store (MongoDB hoặc PostgreSQL).
  - Khi Qdrant trả về top K Child Chunks, dùng `parent_id` để query lên Document Store lấy nguyên văn Parent Document nạp vào LLM.

## 8. Migration Guide
- **Thay component nào**: Thay đổi class `Chunker` hiện tại (Bỏ hàm prepend string).
- **Sửa file nào**: `src/chunker.py` (Chỉ thêm logic gán UUID parent_id thay vì nối chuỗi) và `module2` (Cần kết nối thêm Document Store).
- **Pipeline thay đổi**: Khâu Retrieval ở Module 3 sẽ phải gọi thêm 1 bước Fetch từ Document Store.
- **Dữ liệu**: Bắt buộc re-index toàn bộ dữ liệu (Drop Vector DB và chạy lại Pipeline).
- **Backward compatibility**: Break hoàn toàn cấu trúc cũ. Cần làm trong Major version.
- **Rollback strategy**: Chạy song song 2 Collection trong Qdrant, nếu luồng Parent-Child lỗi, route query về Collection cũ.

## 9. Impact Analysis
- **Chapter 2 (Vector DB)**: Kích thước các Payload sẽ thay đổi (lưu thêm `parent_id`). Nếu áp dụng kiến trúc Parent-Child, cần thêm MongoDB/Postgres.
- **Chapter 3 (Query Pipeline)**: Độ trễ (Latency) tăng lên một chút do phải thêm 1 network call tới Document Store, nhưng chất lượng LLM sẽ hoàn hảo vì thấy toàn bộ bối cảnh xung quanh.

## 10. Risks & Technical Debt
- **Rủi ro**: Nếu văn bản có cấu trúc sâu tới "Tiết" mà Chunker chưa hỗ trợ, nó có thể báo lỗi hoặc phớt lờ.
- **Technical Debt**: Hàm đếm token hiện tại dựa trên số từ (`len(text.split())`) để mô phỏng, thay vì dùng Tokenizer chuẩn (ví dụ tiktoken hoặc AutoTokenizer), dẫn đến đếm không chính xác tuyệt đối. Có thể gây lỗi "vượt token limit" trên thực tế.

## 11. Future Roadmap
1. MVP (Hiện tại): Cắt theo Điều/Khoản + Gắn Prefix thủ công (Prepend string).
2. Production: Chuyển đếm token sang mô hình đếm thực (tiktoken/AutoTokenizer) tương ứng với Embedding Model đang dùng.
3. Enterprise: Kiến trúc Parent-Child Retrieval với Document Store thực thụ.

## 12. References
- [Advanced RAG Techniques: Parent-Child Retrieval (LlamaIndex Docs)](#)
- [Chunking Strategies for Semantic Search (Pinecone Blog)](#)
