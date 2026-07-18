# Chapter 3: Query Pipeline (Online Answering)

Module này thuộc Phase **Query Pipeline**, quản lý toàn bộ quá trình xử lý câu hỏi (Online) của người dùng, tìm kiếm tài liệu từ Vector DB, và sinh ra câu trả lời cuối cùng, đi kèm hệ thống kiểm chứng (Verification Pipeline) chống ảo giác (Hallucination). 

Toàn bộ kiến trúc tuân thủ chặt chẽ nguyên tắc **Interface-First**, **Dependency Injection**, và **Façade + Orchestrator Pattern**.

> **TÀI LIỆU QUAN TRỌNG:** Để hiểu sâu về thuật toán, phân tích kiến trúc, tại sao lại dùng Rule-based kết hợp Reranker, và lộ trình nâng cấp (Production Migration), vui lòng đọc bắt buộc file: **[ENGINEERING_DOCS.md](./ENGINEERING_DOCS.md)** (Tổng quan Tier 1) và các file chi tiết trong thư mục **[adr/](./adr/)** (Chi tiết Tier 2).

---

## 1. Cấu trúc Thư mục

```text
chapter-3-query-pipeline/
├── module3/
│   ├── schemas.py             # Data classes nội bộ: AnswerResult, QueryContext...
│   ├── interfaces.py          # Interfaces chuẩn (Rewriter, Reranker, Verifier...)
│   ├── orchestrator.py        # Façade (QueryPipeline) & QueryOrchestrator
│   ├── query_understanding.py # Chuẩn hóa (Normalizer) và viết lại câu hỏi (Rewriter)
│   ├── reranker.py            # Chấm điểm và lọc lại (Filter) kết quả Retrieval
│   ├── prompt_builder.py      # Dựng Context Window và Prompt gửi LLM
│   ├── generator.py           # Gọi LLM sinh văn bản (Answer Generation)
│   └── verifier.py            # Chốt chặn Groundedness và Citation (Chống ảo giác)
├── evaluation/                # Module đánh giá tự động (với golden_questions)
├── tests/                     # Unit Tests và Integration Tests
├── demo_query_pipeline.py     # Script chạy Demo End-to-End
├── adr/                       # [TIER 2] Architecture Decision Records
├── ENGINEERING_DOCS.md        # [TIER 1] Tài liệu kiến trúc chuyên sâu
└── README.md                  # (File này) Hướng dẫn nhanh
```

---

## 2. Các lớp mô phỏng (Simulation Layers)

Vì đây là module lắp ráp cuối cùng, ở giai đoạn MVP/Local Development, hệ thống đang phụ thuộc nhiều vào các Simulation Layer để mô phỏng LLM và Reranker mạnh (chưa cắm API thật để tiết kiệm chi phí & thời gian setup).

1. **`RuleBasedQueryRewriter`**: Lọc từ khóa cơ bản bằng Regex thay vì dùng LLM (GPT-4/Gemini) viết lại câu hỏi.
2. **`MockReranker` / `RuleBasedReranker`**: Mô phỏng Reranking bằng cách lọc trạng thái và dùng Jaccard Overlap, thay vì dùng `BAAI/bge-reranker-v2-m3`.
3. **`MockLLMGenerator`**: Sinh câu trả lời giả lập (hardcode) theo Regex dựa trên Mock Data thay vì gọi LLM thật.
4. **`MockGroundednessVerifier`**: Chốt chặn bắt từ khóa ảo giác giả lập thay vì dùng Natural Language Inference (NLI) model.

> **Lưu ý Mở rộng**: Chi tiết về cách thức, rủi ro và các bước Migration từ Simulation Layer sang Production Layer được trình bày chi tiết trong thư mục `adr/` (ADR-301, ADR-302, ADR-303, ADR-304, ADR-305).

---

## 3. Cách chạy Demo (Quickstart)

Di chuyển vào thư mục dự án và kích hoạt môi trường ảo (nếu có), đảm bảo bạn đứng ở Root `d:\test` để Python nhận diện các module dùng chung.

```bash
# Bật ép kiểu UTF-8 (rất quan trọng trên Windows)
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONPATH="."

# Chạy Demo
python chapter-3-query-pipeline/demo_query_pipeline.py
```

Kết quả mong đợi: Hệ thống sẽ in ra màn hình console kết quả chạy của 5 kịch bản truy vấn mẫu (Ví dụ: Câu hỏi hợp lệ, Câu hỏi ngoài phạm vi, Câu hỏi không rõ ràng, Câu hỏi trúng văn bản đã hết hiệu lực, và Kiểm tra chống ảo giác). Đi kèm với mỗi kết quả là thời gian đo lường (Telemetry) cho từng bước trong Pipeline.

---

## 4. Chạy Unit Test và Evaluation

Kiểm tra Unit Test để đảm bảo luồng Orchestrator và Verifier hoạt động ổn định:
```bash
$env:PYTHONPATH="."
pytest chapter-3-query-pipeline/tests/
```

Đánh giá độ chính xác (End-to-End Evaluation) dựa trên tập câu hỏi chuẩn (Golden Questions):
```bash
$env:PYTHONPATH="."
python chapter-3-query-pipeline/evaluation/evaluator.py
```
