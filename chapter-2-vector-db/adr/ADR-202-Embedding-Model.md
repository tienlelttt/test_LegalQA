# ADR 202: Lựa chọn Embedding Model (MiniLM vs BGE-M3)

## 1. Context
Quá trình Dense Retrieval đòi hỏi phải mã hóa các câu hỏi và các đoạn Chunk thành không gian Vector sao cho các văn bản có ngữ nghĩa tương đương nằm gần nhau.

## 2. Problem Statement
**Nên sử dụng mô hình Embedding nào để tối ưu cho tiếng Việt, đặc biệt là với các thuật ngữ pháp lý phức tạp?**
Các model lớn (Large models) cho chất lượng tốt nhưng không thể chạy trên CPU của máy tính phát triển (Dev machine).

## 3. Alternatives Considered

**Option A: OpenAI `text-embedding-3-small`**
- **Ưu điểm**: Rất mạnh, không cần quản lý hạ tầng GPU. Context dài (8191 tokens).
- **Nhược điểm**: Tốn phí API tính theo token. Dữ liệu luật có thể chứa văn bản mật (On-premise requirement) không được gửi ra ngoài.
- **Vì sao không chọn**: Do yêu cầu bảo mật có thể phát sinh, ưu tiên mô hình mã nguồn mở.

**Option B: `paraphrase-multilingual-MiniLM-L12-v2`**
- **Ưu điểm**: Siêu nhẹ (~400MB), có thể chạy nhanh trên bất kỳ CPU nào. Rất dễ setup.
- **Nhược điểm**: Vector chiều thấp (384-dim), năng lực thấu hiểu ngữ nghĩa tiếng Việt pháp lý khá yếu. Không hiểu được từ đồng nghĩa phức tạp.
- **Vì sao không chọn cho Production**: Độ chính xác không đạt chuẩn cho pháp lý.

**Option C: `BAAI/bge-m3`**
- **Ưu điểm**: Mô hình Embedding đa ngôn ngữ hàng đầu hiện tại (SOTA), hỗ trợ tiếng Việt cực tốt, kích thước vector 1024-dim, hỗ trợ độ dài text lên đến 8192 tokens. Hỗ trợ tạo Sparse Vectors (BM25) ngay bên trong model.
- **Nhược điểm**: Yêu cầu VRAM GPU (khoảng 4GB-8GB) để chạy mượt mà, quá nặng cho CPU.

## 4. Decision
Quyết định: **Sử dụng Dual-Profile (MiniLM cho Dev, BGE-M3 cho Production)**.
- Môi trường hiện tại (Local) dùng Option B.
- Thiết kế hệ thống lỏng lẻo (Loosely-coupled) cho phép thay đổi sang Option C trong Production chỉ bằng một biến môi trường.

## 5. Trade-offs (8 Trục)
- **Performance**: MiniLM cực nhanh trên CPU. BGE-M3 cực chậm trên CPU nhưng lại cực nhanh trên GPU (nếu dùng Inference Server).
- **Memory**: BGE-M3 tốn tối thiểu 8GB VRAM và tạo ra Vector 1024 chiều, làm Qdrant cũng tốn RAM gấp 3 lần so với MiniLM (384 chiều).
- **Latency**: Nếu Deploy chuẩn trên GPU, BGE-M3 có latency ~30-50ms.
- **Cost**: Chạy BGE-M3 cần thuê Server có GPU (VD: L4 / T4), tốn kém chi phí phần cứng.
- **Complexity**: Việc thay đổi model không tăng độ phức tạp kiến trúc lõi, nhưng việc duy trì Inference Server (TEI) cho BGE-M3 là một thách thức DevOps.
- **Extensibility**: Có thể dễ dàng đổi mô hình mới hơn trong tương lai bằng cách đổi URL API.
- **Maintainability**: Dễ bảo trì phía Application. Khó bảo trì phía Infrastructure.
- **Testability**: Dễ test thông qua cấu hình Dependency Injection.

## 6. Current Implementation
- **Trạng thái**: Hardcode sử dụng `paraphrase-multilingual-MiniLM-L12-v2` trong `demo_indexing.py` và `embedder.py`. Chạy thuần túy trên CPU (`device='cpu'`).
- **Giới hạn**: Kết quả Retrieval đối với các truy vấn ngữ nghĩa phức tạp sẽ không cao.
- **Ảnh hưởng**: Làm giảm điểm số Accuracy End-to-End ở Chapter 3.

## 7. Production Architecture
- Sử dụng mô hình `BGE-M3`.
- Tách mô hình ra khỏi code chính. Deploy mô hình trên **Triton Inference Server** hoặc **TEI (Text-Embeddings-Inference)** của HuggingFace để tận dụng Continuous Batching trên GPU, tối đa hóa thông lượng (Throughput).

## 8. Migration Guide
- **Thay component nào**: Sửa class `Embedder` để thay vì load `SentenceTransformers` cục bộ, nó sẽ gọi REST API/gRPC tới TEI Server.
- **Sửa file nào**: Cập nhật `settings.py` biến `EMBEDDING_MODEL_NAME` và tạo class `TEIEmbedder(EmbedderInterface)`.
- **Pipeline thay đổi**: Quá trình nhúng sẽ đi qua mạng thay vì trong RAM.
- **Dữ liệu**: Bắt buộc tạo Collection mới trên Qdrant (vì số chiều Vector tăng từ 384 lên 1024), và chạy Ingestion Pipeline để nhúng (embed) lại toàn bộ dữ liệu. Không tương thích ngược.
- **Rollback strategy**: Giữ lại Collection cũ của MiniLM. Nếu BGE-M3 lỗi, trỏ tên Collection về lại bảng cũ.

## 9. Impact Analysis
- **Chapter 3 (Query Pipeline)**: Tăng mạnh MRR (Mean Reciprocal Rank) cho hệ thống truy xuất. LLM sẽ nhận được top 5 chunks chất lượng hơn hẳn. Khả năng trả lời đúng tăng vọt.

## 10. Risks & Technical Debt
- **Rủi ro**: Hết VRAM khi có quá nhiều concurrent request nhúng (Embedding) gửi tới TEI server.
- **Technical Debt**: Class `embedder.py` hiện tại load trực tiếp model vào chung RAM của tiến trình Web Server. Ở Production, cách này gây nghẽn cổ chai (Bottleneck) trầm trọng vì Python có GIL. 

## 11. Future Roadmap
1. Simulation (Hiện tại): MiniLM trên CPU (SentenceTransformers).
2. Production: BGE-M3 gọi qua REST API tới GPU Cloud.
3. Enterprise: Cụm Inference Server (TEI) chịu tải cao với Load Balancer.

## 12. References
- [BGE-M3 Paper: Multi-Lingual, Multi-Function, Multi-Granularity Text Embeddings](#)
- [HuggingFace Text Embeddings Inference (TEI)](#)
