# ADR 101: Lựa chọn phương pháp bóc tách cấu trúc (Regex/State Machine vs LLM - Đã loại bỏ hoàn toàn OCR)

## 1. Context
Hệ thống LegalQA cần trích xuất văn bản pháp luật (thường lưu dưới dạng PDF hoặc DOCX) thành cấu trúc cây có thứ bậc (Chương → Mục → Điều → Khoản → Điểm) để LLM có thể dễ dàng tham chiếu. Việc trích xuất thủ công không khả thi do số lượng văn bản luật khổng lồ và được cập nhật liên tục. Hệ thống cần một phương pháp bóc tách tự động, chính xác và có thể mở rộng.

## 2. Problem Statement
Bài toán đặt ra: **Nên sử dụng công nghệ nào để bóc tách cấu trúc văn bản luật hiệu quả nhất?**
Văn bản pháp luật có cấu trúc phân cấp nghiêm ngặt, nhưng đôi khi có nhiễu (header, footer, watermark). Việc sử dụng các công cụ bóc tách NLP hoặc LLM có thể chậm, tốn kém và sinh ra "ảo giác" (nhầm lẫn số Điều). Việc dùng Regex đơn thuần có thể bỏ sót các trường hợp đặc biệt (edge cases).

## 3. Alternatives Considered

**Option A: Mô hình ngôn ngữ lớn (LLM-based Parsing)**
- **Ưu điểm**: Xử lý tốt các văn bản lộn xộn, không cần viết rules phức tạp, dễ bảo trì ban đầu.
- **Nhược điểm**: 
  - Tốc độ cực chậm.
  - Rủi ro sinh ảo giác (thay đổi/lược bỏ nội dung văn bản gốc) gây hệ lụy pháp lý nghiêm trọng.
- **Chi phí**: API quá cao cho Ingestion hàng vạn trang.
- **Vì sao không chọn**: Chi phí và tốc độ không đáp ứng được yêu cầu xử lý hàng triệu trang định kỳ.

**Option B: Regex tĩnh thuần túy (Pure Static Regex)**
- **Ưu điểm**: Nhanh vô song, nhẹ nhàng, dễ triển khai.
- **Nhược điểm**: Khó duy trì ngữ cảnh (không biết Khoản hiện tại đang thuộc Điều nào nếu chỉ dùng Regex).
- **Vì sao không chọn**: Phá vỡ cấu trúc thứ bậc, không tạo được cây cú pháp (Syntax Tree).

**Option C: State Machine kết hợp Regex**
- **Ưu điểm**: Nhanh, theo dõi được trạng thái thứ bậc hoàn hảo. Độ chính xác gần 100% đối với văn bản chuẩn chính quy.
- **Nhược điểm**: Đòi hỏi duy trì Rule-set phức tạp, dễ lỗi hồi quy nếu chuẩn format văn bản thay đổi.

## 4. Decision
Quyết định: **Chọn Option C (State Machine kết hợp Regex)**.
- **Kiến trúc**: Sử dụng Rule-based State Machine để duyệt từng dòng văn bản (đã được làm sạch). Regex được sử dụng để xác định trạng thái chuyển tiếp (ví dụ: đang ở Điều 1, gặp `^1\.\s` thì chuyển sang trạng thái Khoản 1).
- **Component tham gia**: `Parser` (trong `src/parser.py`) và các mô hình dữ liệu Pydantic (`Chuong`, `Dieu`, `Khoan`, `Diem`).

## 5. Trade-offs (8 Trục)
- **Performance**: Tuyệt vời. Cực nhanh (< 0.1s cho hàng trăm trang văn bản).
- **Memory**: Tối ưu. Chỉ load từng file text lên RAM và xử lý dòng, dung lượng bộ nhớ tĩnh (O(N) với N là số dòng).
- **Latency**: Gần bằng 0 do chạy nội bộ (CPU bound), không gọi ra Network.
- **Cost**: $0. Hoàn toàn miễn phí.
- **Complexity**: Vừa phải, nằm ở việc quản lý và duy trì tập luật Regex (Regex Rule-set) khá phức tạp.
- **Extensibility**: Có thể dễ dàng mở rộng thêm các loại Node pháp lý mới bằng cách thêm State vào State Machine.
- **Maintainability**: Khó. Phải đọc hiểu Regex rối rắm, cần viết Test Case bao phủ toàn diện để không phá vỡ logic cũ khi sửa Regex mới.
- **Testability**: Cực kỳ dễ test. Hàm thuần túy (Pure Functions), dễ viết Unit Test cho từng trường hợp xuống dòng.

## 6. Current Implementation
- **Trạng thái**: Rule-based (Regex + State Machine).
- **Giới hạn**: Chỉ xử lý tốt văn bản PDF text-based và DOCX chuẩn. Không hỗ trợ văn bản scan mờ (đã loại bỏ hoàn toàn OCR).
- **Ảnh hưởng**: Hoạt động hoàn hảo cho MVP, đủ để xây dựng pipeline Indexing cục bộ.

## 7. Production Architecture
Kiến trúc Production sẽ giữ nguyên cốt lõi (State Machine + Regex), nhưng được bao bọc bởi một **Orchestrator** có khả năng:
- Chỉ xử lý các văn bản có text layer, từ chối và báo lỗi rõ ràng nếu nhận được ảnh scan (đã loại bỏ hệ thống OCR).
- Có cơ chế Fallback gọi LLM (như Gemini/OpenAI) để bóc tách **riêng lẻ** các trang bị lỗi format quá nặng mà Regex thất bại.

## 8. Migration Guide
- **Thay component nào**: Sửa class `Parser` để thêm error boundary. Khi bắt được ngoại lệ (không nhận ra format), đẩy raw text vào một hàng đợi (Queue) cho LLM xử lý bù (Fallback).
- **Sửa file nào**: `src/parser.py` và `src/ingestor.py`.
- **Dữ liệu**: Không cần migrate, chạy re-index nếu update regex rules.
- **Pipeline thay đổi**: Từ chạy synchronous chuyển sang asynchronous worker queue cho fallback.
- **Backward compatibility**: Regex cũ vẫn được dùng làm luồng chính (Main flow).
- **Rollback strategy**: Chuyển config tắt LLM Fallback nếu phát hiện LLM sinh dữ liệu ảo hoặc chậm pipeline.

## 9. Impact Analysis
- **Chapter 2 (Vector DB)**: Nhận được các Chunk có Metadata cấu trúc cây chính xác, giúp vector hóa và filter hiệu quả hơn.
- **Chapter 3 (Query Pipeline)**: Giúp tính năng Citation sinh ra câu trả lời chứa trích dẫn chính xác (số Điều, Khoản).

## 10. Risks & Technical Debt
- **Rủi ro**: Thay đổi về chuẩn trình bày văn bản hành chính nhà nước có thể làm hỏng Regex đồng loạt.
- **Technical Debt**: Hiện tại bộ Regex chưa phủ hết các biến thể lỗi font chữ cũ (.VnTime chuyển sang Unicode).

## 11. Future Roadmap
1. MVP (Hiện tại): Regex chuẩn + PDF Text.
2. Production: Chỉ hỗ trợ PDF Text (loại bỏ OCR) + Fallback LLM cho format vỡ.
3. Enterprise: Pipeline tự động cảnh báo (Alert) khi Regex confidence thấp và yêu cầu human-in-the-loop review.

## 12. References
- [Nghị định 34/2016/NĐ-CP về thể thức văn bản quy phạm pháp luật](#)
- [Design Patterns: State Pattern (Gang of Four)](#)
