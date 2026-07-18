# Engineering Docs: Vector Database & Embedding (Module 2)

**Giai đoạn**: Document Pipeline (Bước 2)  
**Kiến trúc tương thích**: LegalQA v2

> [!CAUTION]
> **ĐÂY KHÔNG PHẢI LÀ CẤU HÌNH PRODUCTION.**
> Mã nguồn hiện tại được thiết lập như một **Development Profile (Bản phát triển)** tối ưu cho Laptop/PC cá nhân (không yêu cầu GPU, không cần Docker). Tất cả cơ sở dữ liệu (Qdrant, BM25, Graph) đều đang chạy trên RAM tạm thời (`in-memory`). Việc hiểu rõ giới hạn này giúp Kiến trúc sư và Kỹ sư không lầm tưởng hệ thống hiện tại có thể chịu tải hàng triệu vector hay tìm kiếm cực kỳ chính xác. Mọi tài liệu thiết kế bắt buộc phải được cập nhật đồng bộ mỗi khi mã nguồn được cấu hình lên mức Production.

## CHANGELOG
- **Thay đổi**: Tái cấu trúc tài liệu kiến trúc sang mô hình 2-Tier theo chuẩn mới (Tier 1: Tổng quan chuyên sâu, Tier 2: ADR độc lập).
- **Lý do lệch**: Tài liệu cũ gom chung tổng quan và quyết định thiết kế vào một chỗ, thiếu phân tích Trade-offs chi tiết, thiếu Impact Analysis và rủi ro.
- **Kiến trúc cũ**: Một file duy nhất, khá lộn xộn giữa mã code (simulation) và kiến trúc chuẩn.
- **Kiến trúc mới**: File này đóng vai trò Tier 1. Các ADR (Quyết định cụ thể về Qdrant, MiniLM, Hybrid Search, Neo4j) đã được tách ra thư mục `adr/` và viết lại theo chuẩn 12-section.

---

## 1. Giải thích bài toán tổng thể của dự án
Sau khi **Module 1 (Parsing & Chunking)** hoàn tất việc bóc tách văn bản thành các đoạn nhỏ (Chunk) có ý nghĩa, máy tính vẫn chưa thể "hiểu" được chúng. Nếu chỉ dùng SQL `LIKE` hay Elasticsearch tìm kiếm từ khóa, hệ thống sẽ mù tịt trước những câu hỏi đồng nghĩa (Ví dụ: Hỏi "xe máy" nhưng luật ghi "xe mô tô hai bánh").

**Sứ mệnh của Module 2**: 
1. **Embedding**: Chuyển đổi toàn bộ tiếng Việt trong Chunk thành một ma trận số (Dense Vector). Quá trình này giúp các câu đồng nghĩa sẽ có Vector nằm gần nhau trong không gian nhiều chiều.
2. **Storage**: Lưu trữ các Vector này (kèm nguyên bản Text và Metadata từ Module 1) vào một kho dữ liệu đặc biệt (Vector Database) để tốc độ tìm kiếm nhanh như chớp.
3. **Retrieval**: Cung cấp API (Hybrid Search) kết hợp cả khả năng tìm ngữ nghĩa (Dense) và tìm đích danh từ khóa chính xác (Sparse/BM25) cho Module 3.

## 2. Kiến trúc Tổng thể & Luồng Dữ Liệu
Luồng dữ liệu trong Module 2 hoạt động thông qua `IndexPipeline` (`src/index_pipeline.py`) - nơi ráp nối tất cả các thành phần lại với nhau, chia làm 4 công đoạn:

**Bước 1: Dense Embedding (`src/embedder.py`)**
- Nhận `List[Chunk]` từ Module 1.
- Load mô hình AI. Áp dụng kỹ thuật Batching để gộp nhiều câu lại nhúng cùng lúc nhằm tối đa hóa thông lượng. Tạo ra Dense Vectors.

**Bước 2: Qdrant Vector Store (`src/qdrant_store.py`)**
- Xây dựng bảng (Collection) với thước đo Cosine. 
- Sử dụng thuật toán HNSW (Hierarchical Navigable Small World). Các metadata từ Chapter 1 được nhét vào trường Payload. Đẩy Vectors vào Qdrant.

**Bước 3: Sparse Indexer (`src/sparse_indexer.py`)**
- Thuật toán BM25 xây dựng một Inverted Index (chỉ mục ngược) đo lường tần suất từ khóa trong văn bản.

**Bước 4: Graph Store (`src/graph_store.py`)**
- Nhận đầu vào là các Citations (trích dẫn), tạo các Node (Văn bản) và Edge (Quan hệ "Thay thế", "Sửa đổi") đưa vào Graph DB.

## 3. Giải thích Quyết định Kiến trúc & Phân tích Implementation

*(Xem chi tiết đầy đủ tại thư mục `adr/`)*

### 3.1. Vector Database Strategy
- **a. Lý thuyết chuẩn**: Cần Vector DB hỗ trợ HNSW, Scale-out tốt, lọc Payload cực nhanh.
- **b. Alternatives Considered**: 
  - *Pinecone*: Dễ nhưng đóng mã nguồn, lock-in, không hợp On-premise.
  - *Milvus*: Quá nặng nề cho Local Dev.
- **c. Implementation hiện tại**: Dùng Qdrant nhưng chạy ở chế độ In-memory (`location=":memory:"`).
- **d. Phát triển Production**: Deploy Qdrant Cluster (Docker/K8s) với Persistent Storage (WAL).
- **e. Trade-offs**: *Perf*: Cực nhanh. *Memory*: Tốn RAM do HNSW. *Testability*: Siêu dễ. *Cost*: $0.
- **f. Ảnh hưởng chất lượng**: In-memory chạy mượt cho Demo nhưng tắt app là mất sạch dữ liệu, không thể dùng cho thực tế.
- **g. References**: ADR-201. Qdrant Docs.

### 3.2. Embedding Model Strategy
- **a. Lý thuyết chuẩn**: Mô hình SOTA đa ngôn ngữ, vector lớn, context rộng (BAAI/bge-m3).
- **b. Alternatives Considered**: 
  - *OpenAI text-embedding-3*: Rất mạnh nhưng tốn phí, lo ngại bảo mật data nội bộ.
- **c. Implementation hiện tại**: Dùng mô hình siêu nhỏ `paraphrase-multilingual-MiniLM-L12-v2` (384-dim) chạy thẳng trên CPU.
- **d. Phát triển Production**: Tách model sang TEI (Text Embeddings Inference) Server chạy GPU, dùng model `BGE-M3`.
- **e. Trade-offs**: *Perf*: Chậm trên CPU. *Complexity*: Cao khi maintain TEI server. *Cost*: Tốn tiền thuê GPU.
- **f. Ảnh hưởng chất lượng**: MiniLM tiếng Việt quá yếu, truy xuất sai lệch nhiều, kéo tụt điểm Accuracy của toàn hệ thống ở bản Dev.
- **g. References**: ADR-202. BGE-M3 Paper.

### 3.3. Hybrid Search (Dense + Sparse BM25 + RRF)
- **a. Lý thuyết chuẩn**: Bắt buộc có Hybrid để không trượt các câu hỏi Exact Match. Kết hợp bằng RRF.
- **b. Alternatives Considered**: 
  - *Chỉ Dense*: Bỏ sót số hiệu luật.
  - *Dense + Keyword Filter*: Rất giòn (brittle), sai 1 chữ là trả về rỗng.
- **c. Implementation hiện tại**: Dùng `rank_bm25` In-memory. Tokenizer đang dùng khoảng trắng (`split(" ")`).
- **d. Phát triển Production**: Đưa Sparse Index thẳng vào Qdrant (Qdrant Sparse Vectors). Bắt buộc dùng Tokenizer tiếng Việt (`pyvi`).
- **e. Trade-offs**: *Complexity*: Đồng bộ ID giữa Dense và Sparse khá khó. *Memory*: Tốn gấp đôi không gian lưu trữ.
- **f. Ảnh hưởng chất lượng**: Do dùng `split(" ")`, BM25 hiện tại ở bản Dev gần như vô dụng với Tiếng Việt.
- **g. References**: ADR-203.

### 3.4. Knowledge Graph Strategy
- **a. Lý thuyết chuẩn**: Graph Database (Neo4j) để truy xuất đa bước (Multi-hop Cypher queries).
- **b. Alternatives Considered**: RDBMS Recursive Query (chậm, khó code).
- **c. Implementation hiện tại**: Dùng Python Dictionary (`MemoryGraphRepository`).
- **d. Phát triển Production**: Dựng cụm Neo4j, viết Cypher cho `Neo4jGraphRepository`.
- **e. Trade-offs**: *Complexity*: Rào cản lớn khi học Cypher. *Perf*: Neo4j query đa bước cực nhanh. *Cost*: Đắt.
- **f. Ảnh hưởng chất lượng**: Bản Dev chỉ mô phỏng, chưa thực sự query Multi-hop được.
- **g. References**: ADR-204.

## 4. Những điểm khác so với kế hoạch kiến trúc ban đầu
- **Tách biệt Service (Monolithic tạm thời)**:
  - *Thiết kế ban đầu*: Mô hình nhúng (Model) được tách riêng thành API Microservice (Inference Server).
  - *Thực tế làm tắt*: Load model `SentenceTransformers` trực tiếp vào RAM của tiến trình Python chính.
  - *Nhược điểm*: Gây nghẽn cổ chai (Bottleneck) trầm trọng vì Python có GIL, làm chậm toàn bộ Ingestion.
  - *Roadmap*: Cần triển khai HuggingFace TEI Server.
- **Cluster/Phân mảnh (Sharding)**:
  - *Thiết kế ban đầu*: Qdrant chạy Cluster nhiều node.
  - *Thực tế làm tắt*: In-memory Single Node.
  - *Nhược điểm*: Chết Server là mất dữ liệu.

## 5. Chiến lược Phần cứng & GPU (GPU Strategy)
Kiến trúc sư cần lưu ý đặc điểm phân bổ tài nguyên của Module 2:
- **Tầng Vector DB (Qdrant)**: Chỉ cần RAM (Rất nhiều RAM) và CPU. Không cần GPU. Thuật toán HNSW tốn RAM để tải Graph của không gian Vector. Tối thiểu cần **16GB - 32GB RAM** (System Memory) nếu chạy full dataset (hàng triệu chunks).
- **Tầng Sparse / Keyword / Graph**: Chạy trên CPU và System RAM.
- **Tầng AI (Embedding Model)**: **Bắt buộc dùng GPU** ở Production. Nếu dùng model `BGE-M3`, hệ thống cần ít nhất **1x GPU NVIDIA L4 (24GB VRAM)** để cấu hình Batch-size lớn khi Ingestion. Chạy CPU sẽ tốn hàng tháng trời để index xong toàn bộ luật VN.

## 6. Production Roadmap
1. **Bước 1 (Hạ tầng Database & Sparse)**:
   - *Hành động*: Dựng Qdrant qua Docker. Viết `QdrantSparseIndexer` dùng Tokenizer Tiếng Việt. Đổi biến `QDRANT_URL`.
   - *Điều kiện hoàn thành*: Index thử 10,000 chunk, tắt Docker bật lại dữ liệu vẫn còn (Persistent). Sparse Search tìm trúng phóc từ khóa.
2. **Bước 2 (Nâng cấp Embedding Model)**:
   - *Hành động*: Deploy `BGE-M3` lên HuggingFace TEI. Sửa `Embedder` thành REST API Client.
   - *Điều kiện hoàn thành*: Vector chiều dài 1024. Throughput đạt > 500 chunks / giây.
3. **Bước 3 (Knowledge Graph)**:
   - *Hành động*: Khởi tạo Neo4j. Viết `Neo4jGraphRepository`.
   - *Điều kiện hoàn thành*: Truy vấn Cypher "Tìm các văn bản thay thế Luật Đất Đai 2013" trả về kết quả < 100ms.

## 7. Impact Analysis toàn hệ thống
- **Khi nâng cấp Model (Bước 2)**: Ảnh hưởng trực tiếp đến Chapter 1 (phải Ingest lại toàn bộ dữ liệu từ đầu do Vector size đổi từ 384 -> 1024). Đồng thời ảnh hưởng Chapter 3 (câu Query cũng phải gọi Model 1024 để nhúng). Break hoàn toàn backward compatibility của VectorDB cũ.
- **Khi chuyển Qdrant In-memory sang Docker**: Tăng thêm độ trễ mạng (Network Latency) khoảng vài ms ở Chapter 3, nhưng giải phóng RAM cho Web Server.

## 8. Risks & Technical Debt tổng hợp
- **Technical Debt (BM25 Tokenizer)**: Việc dùng `split(" ")` thay vì `pyvi` khiến Hybrid Search hiện tại bị què quặt. Từ khóa sai lệch.
- **Technical Debt (Single Thread Embedding)**: Gọi HuggingFace thẳng trong code đồng bộ Python khiến CPU bị khóa (blocking), hệ thống không scale được khi có nhiều file đẩy vào cùng lúc.
- **Rủi ro (OOM - Out of memory)**: Qdrant HNSW ngốn RAM. Nếu không set cẩn thận giới hạn Payload và Memory-mapped files (mmap) trong cấu hình Qdrant, server sẽ sập vì tràn RAM.

## 9. Migration Guide (Cho các bước Roadmap)
- **Database (Qdrant)**: Trỏ URL IP sang Server thật. Backup Qdrant cũ (nếu có dùng file cục bộ) bằng công cụ Snapshot của Qdrant API. Chạy Re-index dữ liệu.
- **Embedding Model**: Phải tạo Collection (Bảng) mới trên Qdrant với `vector_size=1024`. Không thể tái sử dụng Collection 384 cũ. Chạy Re-index dữ liệu qua model BGE-M3.
- **Sparse Indexer**: Loại bỏ `rank_bm25` (xóa thư viện). Add Dependency `pyvi`. Re-index để tạo cấu trúc Sparse Vector đẩy lên Qdrant chung với Dense.
- **Graph**: Viết batch script chuyên biệt: Query toàn bộ Citation từ Metadata Qdrant và đẩy sang Neo4j, không cần parse lại PDF.
