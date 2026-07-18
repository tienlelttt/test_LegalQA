# ADR 305: Quản lý Configuration (Settings Injection)

## 1. Context
Trong Query Pipeline có rất nhiều thông số nhạy cảm: `Top_K` của Retriever, `Top_K` của Reranker, `Max_tokens` của LLM Context window. Nếu các kỹ sư tự do hardcode các con số này rải rác trong từng file class, việc tinh chỉnh hệ thống (Hyperparameter tuning) sẽ trở thành cơn ác mộng.

## 2. Problem Statement
**Làm sao quản lý các biến cấu hình thống nhất, an toàn, hỗ trợ nạp qua biến môi trường (Environment Variables) mà không để "Magic Numbers" rải rác khắp nơi trong mã nguồn?**

## 3. Alternatives Considered

**Option A: Hardcode trong từng Class**
- **Ưu điểm**: Gõ code nhanh.
- **Nhược điểm**: Không thể thay đổi lúc runtime. Khi muốn deploy lên môi trường Staging/Production khác nhau, phải sửa code.

**Option B: Dùng file `config.json` thuần túy**
- **Ưu điểm**: Gom về một mối.
- **Nhược điểm**: JSON không hỗ trợ ghi chú (comments). Không có cơ chế Validation kiểu dữ liệu (đọc string `"5"` thay vì int `5` sẽ gây crash app).

**Option C: Dùng thư viện `Pydantic BaseSettings` (12-Factor App methodology)**
- **Ưu điểm**: Đọc trực tiếp từ file `.env` hoặc Biến môi trường hệ thống. Có Validation tự động (ép kiểu an toàn). Hỗ trợ giá trị mặc định. Tuân thủ tuyệt đối chuẩn 12-Factor App.

## 4. Decision
Quyết định: **Chọn Option C (Pydantic BaseSettings)**.
- Mọi hằng số, endpoint, cấu hình thuật toán (`MAX_RETRIEVAL_K`, `RERANK_TOP_K`, v.v.) của hệ thống bắt buộc phải được khai báo trong thư mục chung `shared/config/settings.py`.
- Các Class khi khởi tạo phải đọc setting này, không được nhận số ma thuật (magic numbers).

## 5. Trade-offs (8 Trục)
- **Performance**: Pydantic init khá chậm, nhưng vì `Settings` được tạo ở dạng Singleton (load 1 lần duy nhất khi khởi động app), nên thời gian chạy (Runtime) không bị ảnh hưởng.
- **Memory**: Gần như không đáng kể.
- **Latency**: 0ms.
- **Cost**: $0.
- **Complexity**: Dễ tiếp cận.
- **Extensibility**: Tuyệt vời. Thêm biến mới chỉ tốn 1 dòng code.
- **Maintainability**: Siêu dễ bảo trì. Dễ dàng chạy A/B testing thuật toán trên các môi trường Kubernetes khác nhau bằng cách đổi biến môi trường.
- **Testability**: Rất dễ mock object `Settings` để test các nhánh logic khác nhau.

## 6. Current Implementation
- **Trạng thái**: Đã implement (Singleton config ở `shared/config/settings.py`).
- **Giới hạn**: Hoạt động hoàn hảo cho cả 3 Chapter.

## 7. Production Architecture
- Sử dụng trực tiếp `pydantic-settings` kết hợp với hệ thống quản lý Secret của K8s/Docker Swarm.

## 8. Migration Guide
- **Thay component nào**: Không đổi.

## 9. Impact Analysis
- Hệ thống dễ dàng scale trên nhiều container với các tham số khác nhau.

## 10. Risks & Technical Debt
- **Rủi ro**: Lộ Secret Key nếu commit nhầm file `.env` lên Github.
- **Technical Debt**: Cần thêm cơ chế Hot-reload (load lại biến môi trường mà không cần khởi động lại Server) trong tương lai.

## 11. Future Roadmap
1. Simulation (Hiện tại): File `.env` local.
2. Production: K8s ConfigMap & Secrets.
3. Enterprise: Tích hợp với Consul hoặc AWS Parameter Store để fetch cấu hình động qua API.

## 12. References
- [The Twelve-Factor App (Config)](#)
- [Pydantic Settings Documentation](#)
