# ADR 301: Áp dụng Façade & Orchestrator Pattern cho Query Pipeline

## 1. Context
Hệ thống Query Pipeline bao gồm rất nhiều thành phần: Normalizer, Rewriter, Retriever, Reranker, Context Builder, Prompt Builder, LLM Generator và Verification Pipeline. Nếu để các thành phần này giao tiếp trực tiếp với nhau (Spaghetti code) hoặc để Client tự gọi từng bước, hệ thống sẽ trở nên cực kỳ khó bảo trì, khó đo lường và dễ sinh lỗi.

## 2. Problem Statement
**Làm thế nào để đơn giản hóa giao diện sử dụng cho người dùng cuối (Client/API) nhưng vẫn giữ được khả năng kiểm soát chặt chẽ từng bước xử lý bên trong?**
Cần một kiến trúc đủ linh hoạt để thay thế (Inject) các implementation khác nhau (ví dụ từ Mock sang Production) mà không làm vỡ luồng dữ liệu chính.

## 3. Alternatives Considered
**Option A: Monolithic Function (Một hàm khổng lồ)**
- **Nhược điểm**: Rất khó Unit Test. Mọi thứ dính chặt vào nhau (Tightly coupled). Không thể tái sử dụng một phần tử đơn lẻ (ví dụ chỉ gọi Reranker).

**Option B: Agent Router (LLM tự quyết định flow)**
- **Ưu điểm**: Cực kỳ linh hoạt, có thể tự động rẽ nhánh hỏi SQL hoặc DB vector tùy ngữ cảnh.
- **Nhược điểm**: Trong ngành luật, giao quyền tự quyết định (Routing) cho một LLM Agent là cực kỳ rủi ro. Nó có thể bypass khâu kiểm chứng nếu bị thao túng (prompt injection).
- **Vì sao không chọn**: Đặt tính an toàn (Safety) lên trên tính linh hoạt (Flexibility).

**Option C: Façade + Orchestrator Pattern với Dependency Injection**
- **Ưu điểm**: 
  - `Façade` ẩn đi toàn bộ độ phức tạp, chỉ bộc lộ đúng 1 hàm `ask(query)`.
  - `Orchestrator` nhận tất cả các dependencies qua constructor, chịu trách nhiệm truyền dữ liệu từ bước này sang bước kia và đo lường thời gian (Telemetry). Luồng chạy là tĩnh (Static) và tuyệt đối an toàn.

## 4. Decision
Quyết định: **Chọn Option C (Façade + Orchestrator)**.
- **Kiến trúc**: Lớp `QueryOrchestrator` (Điều phối viên) nhận vào các interfaces. `QueryPipeline` đóng vai trò Façade bọc lấy `QueryOrchestrator`. Dòng chảy dữ liệu qua 7 bước là cứng nhắc và không thể đảo lộn.

## 5. Trade-offs (8 Trục)
- **Performance**: Việc bọc qua nhiều interface có overhead siêu nhỏ (vài nanosecond).
- **Memory**: Tối ưu, vì Orchestrator không lưu state sau khi trả lời xong.
- **Latency**: Có thể đo lường dễ dàng nhờ kiến trúc bọc.
- **Cost**: Không ảnh hưởng chi phí.
- **Complexity**: Độ phức tạp ở mức khá khi khởi tạo (phải truyền nhiều interface), nhưng bù lại logic từng module cực kỳ đơn giản.
- **Extensibility**: Rất tốt. Cắm thêm module mới (như Cache) vào Orchestrator dễ dàng.
- **Maintainability**: Cực kỳ dễ bảo trì. Thay component Mock thành Prod chỉ cần sửa cấu hình Dependency Injection.
- **Testability**: Hoàn hảo. Có thể test từng interface riêng lẻ hoặc test toàn bộ Orchestrator bằng cách truyền Mock.

## 6. Current Implementation
- **Trạng thái**: Đã implement tại `module3/orchestrator.py`.
- **Giới hạn**: Khởi tạo thủ công (Hardcode Instantiate) ở file `demo.py`. Hoạt động đồng bộ.
- **Ảnh hưởng**: Hoàn thành xuất sắc nhiệm vụ tách bạch luồng dữ liệu.

## 7. Production Architecture
- Sử dụng framework Dependency Injection (như `Dependency Injector` hoặc FastAPI `Depends`) để tự động hóa việc khởi tạo `QueryOrchestrator` và các singleton.
- Triển khai OpenTelemetry để trace latency qua từng bước trong Orchestrator.

## 8. Migration Guide
- **Thay component nào**: Không cần thay logic Orchestrator. Chỉ thay các đối tượng được inject vào nó (từ Mock sang Prod).
- **Sửa file nào**: Sửa `demo.py` thành `main.py` của FastAPI với DI Container.
- **Backward compatibility**: Không ảnh hưởng.

## 9. Impact Analysis
- Tương lai nếu có tính năng truy vấn án lệ bằng SQL, Orchestrator sẽ được nâng cấp thành **Semantic Router** (Dùng kỹ thuật phân loại nhúng - Embedding Classifier) để rẽ nhánh cố định chứ không thả nổi cho LLM tự quyết định.

## 10. Risks & Technical Debt
- **Technical Debt**: Hiện tại chưa gắn Log Trace ID vào request. Nếu chạy song song nhiều user, log của Orchestrator sẽ trộn lẫn vào nhau.

## 11. Future Roadmap
1. Simulation (Hiện tại): Khởi tạo thủ công các Mock Object.
2. Production: Sử dụng FastAPI Dependency Injection + OpenTelemetry.
3. Enterprise: Tách Orchestrator thành một Microservice độc lập.

## 12. References
- [Design Patterns: Façade (Gang of Four)](#)
- [Clean Architecture (Robert C. Martin)](#)
