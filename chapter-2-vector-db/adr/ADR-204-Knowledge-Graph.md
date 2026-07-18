# ADR 204: Chiến lược lưu trữ Knowledge Graph (Neo4j vs In-memory Simulation)

## 1. Context
LegalQA không chỉ là hệ thống QA thông thường mà đòi hỏi truy vấn liên văn bản (Multi-hop). Khi văn bản A nói "Sửa đổi Điều 1 của Nghị định B", hệ thống cần một "Bộ não" để hiểu và truy xuất theo cầu nối này.

## 2. Problem Statement
**Lưu trữ các quan hệ pháp lý (Citations/Entities) thu thập được từ Module 1 ở đâu để truy xuất Multi-hop hiệu quả nhất?**

## 3. Alternatives Considered

**Option A: RDBMS (PostgreSQL/MySQL) với Recursive Query**
- **Ưu điểm**: Công nghệ quen thuộc, đã có sẵn trong các stack hệ thống doanh nghiệp.
- **Nhược điểm**: Truy vấn đệ quy (CTE) trên các bảng quan hệ rất phức tạp và cực kỳ chậm khi số lượng node lớn. Không tối ưu cho việc duyệt đồ thị (Graph Traversal).

**Option B: Neo4j (Graph Database)**
- **Ưu điểm**: Chuẩn mực công nghiệp cho Knowledge Graph. Truy vấn ngôn ngữ Cypher mạnh mẽ (vd: `MATCH (v1)-[:SUA_DOI]->(v2) RETURN v2`). Hỗ trợ hiển thị trực quan (Visualization) xuất sắc, giúp kiểm chứng dữ liệu dễ dàng.
- **Nhược điểm**: Nặng nề, khó setup cho lập trình viên ở giai đoạn MVP. Cần dung lượng RAM lớn để lưu Graph trên memory. Khó học ngôn ngữ Cypher.

**Option C: In-memory Dictionary (Simulation)**
- **Ưu điểm**: Siêu tốc độ, không cần cài đặt hạ tầng, không tốn tài nguyên. Dễ dàng code bằng cấu trúc dữ liệu Python chuẩn.
- **Nhược điểm**: Không có tính vĩnh cửu. Không hỗ trợ truy vấn phức tạp (chỉ get trực tiếp key-value). Không scale được.

## 4. Decision
Quyết định: **Sử dụng Dual-Profile (Option C cho MVP, Option B cho Production)**.
Hệ thống tuân thủ Interface-First: Bắt đầu với Option C để dựng luồng logic, và dễ dàng cắm Option B vào khi cần mang lên Production.

## 5. Trade-offs (8 Trục)
- **Performance**: In-memory (O(1)) nhanh hơn Neo4j rất nhiều. Tuy nhiên, nếu duyệt đa bước (Multi-hop) thì tự code DFS/BFS trên In-memory sẽ chậm hơn Neo4j (đã được tối ưu ở tầng C++).
- **Memory**: Neo4j là phần mềm "ngốn" RAM. Cần tối thiểu 4-8GB cho db cỡ nhỏ.
- **Latency**: Có độ trễ mạng nếu gọi Neo4j qua network, nhưng xử lý Traversal lại siêu nhanh.
- **Cost**: Neo4j có bản Community Free, hoặc dùng Neo4j AuraDB (Managed Cloud) khá đắt đỏ.
- **Complexity**: Chuyển từ SQL sang Tư duy Đồ thị (Graph thinking) là rào cản lớn cho team kỹ sư.
- **Extensibility**: Neo4j cực kỳ dễ mở rộng thêm các mối quan hệ (Edges) mới mà không cần migration schema.
- **Maintainability**: Yêu cầu bảo trì server Neo4j riêng biệt.
- **Testability**: In-memory dễ test hơn nhiều. Neo4j yêu cầu Mock data hoặc dựng TestContainer.

## 6. Current Implementation
- **Trạng thái**: Lớp `MemoryGraphRepository` (trong `src/graph_store.py`) sử dụng Python Dictionary (`Dict[str, List[Edge]]`) để lưu các quan hệ.
- **Giới hạn**: Chỉ mô phỏng cấu trúc đơn giản, không hỗ trợ truy vấn Cypher phức tạp (như "tìm khoảng cách ngắn nhất giữa văn bản A và B" hoặc "đếm tổng số văn bản bị sửa đổi bởi cụm văn bản X").
- **Ảnh hưởng**: Phục vụ đủ nhu cầu test cho Chapter 3, nhưng không giải quyết được bài toán thực tiễn.

## 7. Production Architecture
- Database: Cụm **Neo4j** (AuraDB trên Cloud hoặc tự host qua Docker).
- Tích hợp: Viết lớp `Neo4jGraphRepository` dùng `neo4j-driver` để query trực tiếp bằng ngôn ngữ Cypher.
- Cấu trúc Node: `LegalDocument` (id, title, status).
- Cấu trúc Edge: `REPLACES`, `AMENDS`, `REFERENCES`.

## 8. Migration Guide
- **Thay component nào**: Xóa/giữ `MemoryGraphRepository`. Viết class mới `Neo4jGraphRepository` implement `GraphRepositoryInterface`.
- **Sửa file nào**: `settings.py` (cấu hình NEO4J_URI) và `graph_store.py`.
- **Dữ liệu**: Chạy batch script để push toàn bộ dữ liệu Citation/Metadata từ file thô lên Neo4j. Quá trình này có thể tốn vài giờ tùy số lượng văn bản.
- **Rollback strategy**: Nếu Neo4j quá tải, tắt tính năng GraphRAG ở Module 3 (fallback về thuần Vector QA).

## 9. Impact Analysis
- **Chapter 3 (Query Pipeline)**: Kích hoạt được tính năng **Graph Traversal** (Agent duyệt đồ thị liên kết trước khi trả lời). Giải quyết triệt để vấn đề "trả lời dựa trên luật cũ đã bị sửa đổi".

## 10. Risks & Technical Debt
- **Rủi ro**: Tránh sa đà vào GraphRAG quá sớm khi chất lượng Dense Retrieval cơ bản chưa được đảm bảo. GraphRAG chỉ phát huy tác dụng khi quá trình Entity Extraction ở Module 1 có độ chính xác >90%. Nếu Entity sai, Graph sẽ chằng chịt rác.
- **Technical Debt**: Hiện tại Interface `get_related_documents` thiết kế hơi đơn giản, có thể không hứng được hết sức mạnh của các câu Cypher phức tạp.

## 11. Future Roadmap
1. Simulation (Hiện tại): Memory Graph.
2. Production: Neo4j kết hợp Cypher Injection an toàn.
3. Enterprise: Kết hợp Vector DB và Graph DB vào chung một kiến trúc (Vector Node Search -> Graph Traversal).

## 12. References
- [Neo4j Developer Guide](#)
- [Microsoft GraphRAG Architecture](#)
