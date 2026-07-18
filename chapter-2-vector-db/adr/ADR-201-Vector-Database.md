# ADR 201: Lựa chọn Vector Database

## 1. Context
Sau khi Module 1 bóc tách thành công văn bản luật thành hàng trăm ngàn Chunk, hệ thống cần một cơ sở dữ liệu chuyên dụng để lưu trữ các Dense Vector và phục vụ truy vấn Semantic Search với độ trễ cực thấp (< 50ms) ngay cả khi dữ liệu phình to.

## 2. Problem Statement
**Nên sử dụng Vector Database nào để tối ưu cho cả môi trường phát triển (Local) và thực tế (Production), đồng thời hỗ trợ Metadata Filtering tốc độ cao?**
Môi trường phát triển yêu cầu CSDL nhẹ, dễ setup để các kỹ sư không bị "kẹt" ở khâu cài đặt hạ tầng. Tuy nhiên, môi trường Production lại cần khả năng Scale-out và chịu lỗi (Fault Tolerance).

## 3. Alternatives Considered

**Option A: Pinecone (Managed SaaS)**
- **Ưu điểm**: Zero-setup, cực kỳ dễ dùng, hiệu năng cao.
- **Nhược điểm**: Đóng cửa mã nguồn (Closed-source), chi phí cao khi lưu trữ lượng dữ liệu lớn. Phụ thuộc hoàn toàn vào cloud (Vendor lock-in).
- **Vì sao không chọn**: Hệ thống LegalQA có thể chứa dữ liệu nội bộ (On-premise requirement), do đó không phù hợp dùng SaaS công cộng.

**Option B: Milvus**
- **Ưu điểm**: Open-source, hỗ trợ Scale-out xuất sắc, phổ biến trong các Enterprise lớn.
- **Nhược điểm**: Nặng, yêu cầu nhiều component (Etcd, MinIO) qua Docker Compose. Rất khó chạy cục bộ (local) cho các developer có máy tính yếu.
- **Vì sao không chọn**: Quá nặng nề cho môi trường phát triển cục bộ của Developer, đi ngược lại tiêu chí "Simulation Layer" dễ dàng setup.

**Option C: Qdrant**
- **Ưu điểm**: Viết bằng Rust (cực kỳ tối ưu RAM), hỗ trợ chạy In-memory (`:memory:`) hoặc file cục bộ cho Local Dev, và hỗ trợ Cluster cho Production. Hỗ trợ Payload (Metadata) filtering rất mạnh với HNSW.
- **Nhược điểm**: Cộng đồng nhỏ hơn Milvus một chút.

## 4. Decision
Quyết định: **Chọn Option C (Qdrant)**.
- **Kiến trúc**: Sử dụng `QdrantClient`. Ở môi trường Dev, hệ thống gọi `:memory:` để test nhanh Ingestion Pipeline. Ở Production, hệ thống gọi qua gRPC/HTTP tới cụm Qdrant Cluster.
- **Component tham gia**: `LegalVectorStore` trong `src/qdrant_store.py`.

## 5. Trade-offs (8 Trục)
- **Performance**: Tốc độ Insert và Search xuất sắc nhờ viết bằng Rust và thuật toán HNSW.
- **Memory**: Tốn RAM để lưu trữ HNSW Index trong memory khi chạy local, nhưng tiết kiệm hơn Milvus. Ở Production yêu cầu server RAM lớn (16GB+).
- **Latency**: Siêu thấp (thường <20ms cho Semantic Search).
- **Cost**: Open-source, miễn phí hoàn toàn nếu tự host.
- **Complexity**: Vận hành Cluster khá phức tạp (cần cấu hình Snapshot, WAL).
- **Extensibility**: Tốt. Qdrant hỗ trợ Sparse Vectors, có thể gộp chung Dense và Sparse vào cùng 1 bảng.
- **Maintainability**: Dễ bảo trì, API Python thiết kế thân thiện.
- **Testability**: Cực kỳ dễ test nhờ khả năng mock In-memory (`location=":memory:"`), không cần khởi động container.

## 6. Current Implementation
- **Trạng thái**: Đang chạy Qdrant chế độ In-memory (`location=":memory:"`).
- **Giới hạn**: Dữ liệu Vector sẽ bị xóa sạch mỗi khi script Python dừng hoạt động. Không phù hợp lưu trữ lâu dài.
- **Ảnh hưởng**: Phục vụ hoàn hảo cho Unit Test và chạy Demo mà không cần dựng Docker.

## 7. Production Architecture
- Sử dụng Qdrant Server chạy qua Docker (hoặc Kubernetes).
- Cấu hình persistent storage (`/qdrant/storage`).
- Bật tính năng `Write-Ahead-Log (WAL)` để chống mất dữ liệu khi sập nguồn.
- Chạy Multi-node cluster để phân mảnh dữ liệu (Sharding).

## 8. Migration Guide
- **Thay component nào**: Không cần thay component. Chỉ cần cấu hình lại hàm khởi tạo `QdrantClient`.
- **Sửa file nào**: Sửa `settings.py` để trỏ `QDRANT_URL` tới địa chỉ IP của server thật thay vì dùng rỗng/`:memory:`.
- **Pipeline thay đổi**: Khâu Ingestion cần chia Batch nhỏ hơn và add retry để tránh timeout khi call API qua mạng thật.
- **Dữ liệu**: Chạy Ingestion Pipeline một lần duy nhất để đẩy toàn bộ Chunk từ File thô lên Qdrant Server.
- **Backward compatibility**: Giữ nguyên toàn bộ Interface `VectorStoreInterface`.
- **Rollback strategy**: Trỏ URL về lại in-memory hoặc file local nếu Server sập.

## 9. Impact Analysis
- **Chapter 3 (Query Pipeline)**: Độ trễ mạng (Network Latency) sẽ tăng khoảng 5-10ms do gọi Qdrant Server qua mạng thay vì chạy trên RAM của process Python hiện tại, nhưng bộ nhớ RAM của Application server sẽ được giải phóng hoàn toàn, giúp hệ thống chịu tải concurrent users cao hơn.

## 10. Risks & Technical Debt
- **Rủi ro**: 
  - HNSW Index ngốn RAM rất mạnh. Nếu số lượng văn bản luật quá lớn (hàng triệu chunk), Server sẽ OOM (Out of Memory).
- **Technical Debt**: 
  - Chưa bật cơ chế Snapshot / Backup tự động cho Qdrant. Nếu dữ liệu bị hỏng, phải Ingest lại từ đầu, mất hàng tuần.
  - Hiện tại code chưa xử lý lỗi Connection Timeout khi Qdrant Server quá tải.

## 11. Future Roadmap
1. Simulation/Local (Hiện tại): In-memory Qdrant.
2. Production: Qdrant Single Node (Docker) + Backup Snapshot hằng tuần.
3. Enterprise: Qdrant Distributed Cluster với cơ chế replication rập khuôn (Sharding) trên Kubernetes.

## 12. References
- [Qdrant Architecture Documentation](#)
- [HNSW Algorithm Explanation](#)
