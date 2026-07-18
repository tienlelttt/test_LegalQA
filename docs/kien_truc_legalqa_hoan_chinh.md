# Kiến trúc hệ thống LegalQA — Tài liệu hoàn chỉnh và hợp nhất

Đây là bản tổng hợp cuối cùng của kiến trúc hệ thống LegalQA, kết hợp toàn bộ các khung thiết kế, tối ưu từ các phiên bản trước và **đã loại bỏ hoàn toàn các thành phần liên quan đến OCR** theo yêu cầu để tinh gọn hệ thống.

**Cấu trúc tài liệu:**
- Cấp 1: Bức tranh tổng thể
- Cấp 2: Sơ đồ chi tiết đầy đủ
- Cấp 3: Giải thích từng bước chi tiết (mục đích, công nghệ, lý do chọn, cách triển khai)
- Cấp 4: Lộ trình triển khai production theo giai đoạn

---

## CẤP 1 — Bức tranh tổng thể

Hệ thống gồm 3 khối lớn hoạt động song song để đảm bảo tính thực tế cho production:

```text
┌──────────────────────┐     ┌──────────────────────┐
│   DOCUMENT PIPELINE  │     │    QUERY PIPELINE    │
│      (Offline)       │────▶│      (Online)        │
│  Văn bản → 3 kho index│     │  Câu hỏi → Câu trả lời│
└──────────────────────┘     └──────────────────────┘
            ▲                            │
            │                            ▼
┌──────────────────────────────────────────────────┐
│              OPS LAYER (chạy song song)          │
│  Incremental Index · Evaluation · Monitoring ·   │
│  Cache (3 lớp) · Feedback Loop có kiểm duyệt ·   │
│  Security                                        │
└──────────────────────────────────────────────────┘
```

**Vì sao phải có 3 khối, không phải 2:**
Document Pipeline và Query Pipeline là phần "làm ra câu trả lời". Tuy nhiên, văn bản luật thay đổi liên tục, và hệ thống cần kiểm soát chất lượng (đo lường độ chính xác, vòng lặp phản hồi). Ops Layer đảm bảo hệ thống cập nhật được, đo lường được và cải thiện được theo thời gian.

---

## CẤP 2 — Sơ đồ chi tiết đầy đủ

### 2.1. Document Pipeline (Offline)

```text
Legal Documents (PDF text-based, HTML, DOCX)
        │
        ▼
[1] Ingest & Extract Text (Trích xuất trực tiếp, không dùng OCR)
        │
        ▼
[2] Layout Analysis (font, bbox → heading candidate)
        │
        ▼
[3] Legal Structure Parsing (Chương/Điều/Khoản/Điểm)
        │
        ▼
[4] Cleaning (bảo vệ pattern Điều/Khoản)
        │
        ▼
[5] Citation Extraction (viện dẫn nội bộ: "căn cứ Điều X Luật Y")
        │
        ▼
[6] Metadata Extraction (số hiệu, ngày hiệu lực, cơ quan, trạng thái)
        │
        ▼
[7] Version Linking ──▶ Version Graph (văn bản A bị thay bởi văn bản B)
        │
        ▼
[8] Adaptive Legal Chunking 
    (Điều ngắn = 1 chunk; Điều dài = tách Khoản/Điểm; 
     liên kết prev/next Điều làm Context Window)
        │
        ├── [9a] Dense Embedding ─────────► Vector DB (có payload metadata filter)
        ├── [9b] Sparse Index (BM25) ─────► Inverted Index (có term filter)
        └── [9c] Entity & Relation ───────► Knowledge Graph (gộp cả Version Graph)
```

### 2.2. Query Pipeline (Online)

```text
Question
        │
        ▼
[1] Query Understanding
    (Spell Correction → Legal Entity Recognition → Intent Detection →
     Metadata Detection → Query Rewrite → Self-Query)
        │
        ▼
[2] Planner / Router (rule-based)
    - Có số Điều/mã văn bản cụ thể?   → bỏ qua HyDE
    - Multi-hop / so sánh?            → bật Graph traversal
    - Nhắc "hiện hành/mới nhất"?      → filter status = effective
        │
        ├── [3] Metadata Filter (áp trước retrieval)
        ├── [4] Query Expansion có điều kiện (HyDE / Multi-query)
        ▼
[5] Hybrid Retrieval (BM25 + Dense + Graph traversal có chọn lọc)
        │
        ▼
[6] Reciprocal Rank Fusion
        │
        ▼
[7] Cross-Encoder Reranker + Rule-based Boost
    (neural score + boost theo hiệu lực + boost theo độ tin cậy)
        │
        ▼
[8] Context Builder (child chunk trúng → lấy parent chunk đầy đủ)
        │
        ▼
[9] Prompt Builder
    System Prompt → Legal Constraints → Retrieved Context →
    Citation Rules → Output Format → Few-shot → Question
        │
        ▼
[10] LLM Router (chọn model theo độ phức tạp câu hỏi)
        │
        ▼
[11] Groundedness Check (nội dung có được context hỗ trợ?)
        │
        ▼
[12] Citation Verification (số Điều/Khoản trích có khớp đúng chunk?)
        │
        ▼
[13] Hallucination Detection (tổng hợp 11+12 → mức rủi ro)
        │
   ┌────┴────┐
  Đạt      Không đạt
   │            │
   ▼            ▼
[14] Confidence   "Không đủ căn cứ
     Scoring       để trả lời"
   │
   ▼
Answer
```

---

## CẤP 3 — Chi tiết từng bước: mục đích, công nghệ, lý do chọn, cách triển khai

### A. DOCUMENT PIPELINE

**[1] Ingest & Extract Text**
- **Mục đích**: Đưa file nhị phân về text có giữ layout (để nhận diện heading Điều/Khoản sau này).
- **Công nghệ đề xuất**: `PyMuPDF` (fitz) hoặc `pdfplumber` cho PDF text-based; `python-docx` cho DOCX; `BeautifulSoup` cho HTML.
- **Vì sao chọn PyMuPDF**: Giữ được tọa độ và font-size của từng dòng, cần thiết để suy ra heading (Điều thường in đậm/cỡ chữ khác) mà không cần OCR; nhanh và chính xác trên văn bản gốc (born-digital).
- **Quyết định bỏ OCR — đánh đổi cần biết:** Hệ thống giả định toàn bộ input là PDF gốc/HTML/DOCX có text layer sẵn (đúng với phần lớn văn bản pháp luật do cơ quan nhà nước phát hành/tải từ cổng thông tin chính thức). Đánh đổi: nếu tương lai có văn bản chỉ tồn tại dưới dạng bản scan (ảnh), hệ thống **sẽ không đọc được** vì không có nhánh dự phòng. Nên thêm một bước kiểm tra đầu vào (validation): nếu `page.get_text()` trả về gần rỗng cho một file bất kỳ, hệ thống cần **từ chối và báo lỗi rõ ràng** ("file không có text layer, cần OCR trước khi nạp") thay vì âm thầm tạo ra chunk rỗng — tránh lỗi âm thầm lan xuống toàn bộ pipeline.
- **Cách triển khai**:
  - Detect loại file → route sang parser tương ứng.
  - Extract bằng `page.get_text("dict")` (PyMuPDF) — trả về cả text và font info trong cùng một lần gọi.
  - Validation gate: nếu `len(text)/số_trang` dưới ngưỡng tối thiểu (ví dụ 50 ký tự/trang) → reject file, ghi log cảnh báo, không đẩy tiếp vào pipeline.
  - Lưu output dưới dạng JSON trung gian: `{"page": n, "text": "...", "font_size": x, "bold": true/false, "bbox": [...]}` cho từng dòng — input cho bước Layout Analysis và Legal Structure Parser.

**[2] Layout Analysis**
- **Mục đích**: Tổ chức lại thông tin font-size/độ đậm/tọa độ đã lấy được ở bước [1] thành "ứng viên heading" — dòng nào có khả năng là Chương/Điều/Khoản dựa trên đặc điểm trình bày (in đậm, cỡ chữ lớn hơn, thụt lề đặc trưng), trước khi áp quy tắc ngôn ngữ ở bước [3].
- **Vì sao tách thành bước riêng thay vì gộp vào [1]**: tách bạch "trích xuất dữ liệu thô" (bước 1) khỏi "diễn giải ý nghĩa trình bày" (bước 2) giúp dễ debug hơn khi heading bị nhận diện sai — có thể kiểm tra riêng từng lớp.
- **Cách triển khai**: gắn nhãn tạm `is_heading_candidate=True/False` cho từng dòng dựa trên so sánh font-size với font-size trung vị của toàn văn bản (dòng có font lớn hơn hoặc in đậm khác biệt → candidate).

**[3] Legal Structure Parsing**
- **Mục đích**: Dựng cây cấu trúc Chương → Mục → Điều → Khoản → Điểm từ text còn nguyên (chưa qua Cleaning) kết hợp thông tin candidate ở bước [2].
- **Công nghệ**: Regex theo pattern chuẩn của văn bản luật VN (`^Điều\s+\d+\.`, `^\d+\.\s`, `^[a-z]\)\s`) kết hợp cờ `is_heading_candidate` để phân biệt heading thật với số liệt kê xuất hiện trong nội dung (ví dụ "khoản 2" được nhắc lại trong một câu văn không phải là heading Khoản 2 thật).
- **Vì sao chạy trước Cleaning, không phải sau**: cây cấu trúc cần dựng trên text còn đầy đủ để không bỏ lỡ heading nếu bước Cleaning lỡ xóa nhầm; ngược lại, việc dựng cây xong **giúp bước Cleaning ở [4] biết chính xác dòng nào là Điều/Khoản thật để bảo vệ**, tránh xóa nhầm. Đây là quan hệ hai chiều: Layout Analysis phục vụ Structure Parsing, và Structure Parsing phục vụ Cleaning an toàn hơn.
- **Vì sao không dùng LLM để parse cấu trúc**: Văn bản luật VN có format đánh số cực kỳ tường minh và nhất quán theo Nghị định về thể thức văn bản — dùng regex cho kết quả chính xác gần như tuyệt đối với chi phí gần bằng 0, trong khi dùng LLM tốn chi phí, chậm, và có xác suất lỗi cao hơn cho một việc mà rule-based làm tốt hơn.
- **Cách triển khai**:
  - Duyệt từng dòng (đã có layout info), áp regex theo thứ tự ưu tiên: Chương → Mục → Điều → Khoản → Điểm.
  - Dựng cây (nested dict hoặc dùng thư viện `anytree`), mỗi node giữ text nội dung thô và reference đến node cha.
  - Output: JSON cây cấu trúc + text gốc gắn `node_id`.

**[4] Cleaning**
- **Mục đích**: Loại header/footer lặp lại, số trang, watermark, lỗi encoding — mà không xóa nhầm nội dung Điều/Khoản đã được xác định ở bước [3].
- **Công nghệ**: Rule-based bằng regex + heuristic phát hiện dòng lặp lại trên >70% số trang (đặc trưng của header/footer).
- **Vì sao rule-based, không dùng model**: Với domain hẹp (một loại văn bản hành chính có format khá đồng nhất), regex đơn giản, dễ audit, dễ debug hơn nhiều so với dùng LLM để "làm sạch" — dùng LLM ở bước này là lãng phí chi phí và tạo rủi ro thay đổi nội dung ngoài ý muốn.
- **Cách triển khai**:
  - Thống kê tần suất xuất hiện của mỗi dòng text trên toàn văn bản → dòng nào lặp lại ở vị trí đầu/cuối trang với tần suất cao và **không nằm trong node nào của cây cấu trúc ở bước [3]** → đánh dấu header/footer, loại bỏ.
  - Vì cây cấu trúc đã dựng xong, việc "bảo vệ" nội dung Điều/Khoản không cần whitelist regex phỏng đoán nữa — chỉ cần kiểm tra dòng đó có thuộc một node đã được parse hay không, chính xác hơn nhiều so với whitelist regex đơn thuần.
- **Sai lầm thường gặp**: Chạy Cleaning trước khi dựng cây cấu trúc (thứ tự cũ, sai) — khi đó phải đoán pattern để bảo vệ, dễ xóa nhầm số Điều đứng đầu dòng nếu regex bảo vệ chưa cover hết biến thể trình bày.

**[5] Citation Extraction**
- **Mục đích**: Trích các viện dẫn nội bộ xuất hiện *trong nội dung* từng Điều — ví dụ "căn cứ Điều 12 Luật Đất đai 2013" nằm bên trong một Điều của văn bản khác. Đây là dữ liệu cấp câu/đoạn, khác với Metadata Extraction ở bước [6] vốn chạy ở cấp toàn văn bản.
- **Vì sao phải tách thành bước riêng, không gộp vào Metadata Extraction**: nếu gộp chung, việc trích xuất chỉ chạy một lần ở cấp văn bản sẽ bỏ sót các viện dẫn nằm sâu trong từng Điều — trong khi đây chính là input trực tiếp để dựng cạnh (edge) cho Knowledge Graph ở bước [9c].
- **Công nghệ**: Regex chạy trên từng node Điều đã có từ cây cấu trúc ở bước [3]: pattern `Điều\s+\d+.*(Luật|Nghị định|Thông tư)\s+.+`.
- **Cách triển khai**: duyệt từng node Điều, áp regex tìm câu dẫn chiếu, output là danh sách cạnh có hướng `(Điều nguồn, VIỆN_DẪN, Điều/văn bản đích)` — lưu tạm, sẽ nạp vào Knowledge Graph cùng lúc với Version Linking ở bước [7].

**[6] Metadata Extraction**
- **Mục đích**: Trích metadata cấp văn bản: loại văn bản, số hiệu, ngày ban hành, ngày hiệu lực, cơ quan ban hành, trạng thái hiệu lực, quan hệ sửa đổi/thay thế với văn bản khác.
- **Công nghệ**: Regex cho trường có format cố định (số hiệu văn bản luôn theo mẫu `số .../năm/LOẠI-CƠQUAN`); NER model (hoặc LLM nhỏ với prompt trích xuất có schema JSON cố định) cho câu dẫn chiếu tự do kiểu "sửa đổi, bổ sung một số điều của...".
- **Vì sao kết hợp cả regex và LLM thay vì chỉ chọn một**: Các trường có cấu trúc chuẩn (số hiệu, ngày) dùng regex cho độ chính xác gần 100% và chi phí thấp; nhưng câu dẫn chiếu sửa đổi/thay thế thường diễn đạt tự do bằng ngôn ngữ tự nhiên, regex không cover hết các biến thể — cần LLM (bắt buộc structured output/JSON schema) để trích xuất linh hoạt hơn. Kết hợp cả hai tận dụng ưu điểm của từng phương pháp.
- **Cách triển khai**:
  - Regex-first: chạy các pattern cố định trước, điền vào schema metadata.
  - Với các trường còn thiếu (đặc biệt quan hệ sửa đổi/thay thế), gọi LLM với prompt ép output JSON đúng schema, ví dụ: `{"amends": ["số .../NĐ-CP"], "amended_by": null, "status": "hiệu lực"}`.
  - **Bước quan trọng nhất**: metadata này phải được lan truyền xuống từng chunk ở bước [8], không chỉ lưu ở cấp document — nếu không, Citation Verification ở Query Pipeline sẽ không biết chunk cụ thể thuộc Điều nào.

**[7] Version Linking → Version Graph**
- **Mục đích**: Biểu diễn quan hệ "văn bản A bị thay thế/sửa đổi bởi văn bản B" như một cạnh có hướng, có thời gian hiệu lực đi kèm — không phải một field metadata phẳng.
- **Vì sao không thể chỉ là metadata (`status: hết hiệu lực`)**: nếu chỉ lưu trạng thái phẳng, hệ thống biết văn bản cũ đã hết hiệu lực nhưng **không tự biết văn bản nào thay thế nó** để gợi ý lại cho người dùng. Ví dụ Luật Đất đai 2013 bị thay bởi Luật Đất đai 2024 — cần một bước graph traversal 1 cấp để tự động tìm ra văn bản thay thế khi retrieval trả về văn bản cũ.
- **Công nghệ**: rule-based, trích từ câu mở đầu văn bản dạng "Luật này thay thế Luật số .../20xx/QH..." hoặc từ trường `amends`/`amended_by` đã trích ở bước [6].
- **Cách triển khai**: tạo cạnh `THAY_THE`/`SUA_DOI`/`BAI_BO` giữa 2 node văn bản trong Knowledge Graph (nạp cùng lúc với cạnh Citation Extraction ở bước [5]), có thuộc tính `ngày_có_hiệu_lực` trên cạnh. Khi Query Pipeline retrieval trả về một văn bản `status=hết hiệu lực`, hệ thống truy vấn graph thêm 1 bước để lấy văn bản thay thế, đưa cả hai vào context kèm ghi chú rõ ràng.

**[8] Adaptive Legal Chunking**
- **Mục đích**: Chia văn bản thành đơn vị index hóa vừa đủ nhỏ để embedding chính xác, vừa đủ lớn để giữ trọn ngữ nghĩa một quy định.
- **Chiến lược**: Parent-Child hierarchical chunking — parent chunk = toàn bộ Điều, child chunk = từng Khoản (hoặc Điểm nếu Khoản còn dài).
- **Vì sao chọn parent-child thay vì fixed-size chunking**: Fixed-size (ví dụ 512 token cố định) không tôn trọng ranh giới ngữ nghĩa của Điều/Khoản — dễ cắt ngang khiến một Điểm bị tách khỏi Khoản chứa điều kiện áp dụng của nó, làm LLM hiểu sai hoặc thiếu ngữ cảnh khi trả lời. Parent-child giải quyết mâu thuẫn giữa "chunk nhỏ để matching chính xác" (dùng child để embed/retrieve) và "chunk đủ lớn để LLM có ngữ cảnh" (dùng parent để đưa vào prompt sau khi retrieve trúng child).
- **Cách triển khai**:
  - Với mỗi Điều trong cây cấu trúc từ bước [3]: nếu độ dài dưới ngưỡng token của embedding model (thường 512-1024 token) → dùng nguyên Điều làm một chunk duy nhất (parent = child).
  - Nếu Điều dài hơn ngưỡng → tách theo Khoản, mỗi Khoản là một child chunk, nhưng thêm prefix ngữ cảnh vào đầu mỗi child trước khi embed: `"[Điều 12 - Nghị định .../NĐ-CP] Khoản 2: ..."` — kỹ thuật này (contextual chunk prefixing) giúp vector của child chunk vẫn "biết" nó thuộc văn bản/Điều nào dù bị tách rời.
  - Lưu quan hệ `parent_id` — `child_id` trong metadata store (có thể dùng chính field trong Vector DB hoặc một bảng quan hệ riêng trong PostgreSQL).
  - Gắn đầy đủ metadata đã trích ở bước [4] vào từng chunk: `document_id`, `dieu_so`, `khoan_so`, `diem`, `hieu_luc_tu_ngay`, `trang_thai`.

**[9a] Dense Embedding → Vector DB**
- **Mục đích**: Biểu diễn ngữ nghĩa chunk thành vector để tìm kiếm theo độ tương đồng.
- **Model đề xuất**: `BGE-M3` hoặc `multilingual-e5-large` — cả hai là embedding đa ngôn ngữ open-source có hỗ trợ tiếng Việt tốt và đã được kiểm chứng rộng rãi trong các benchmark retrieval đa ngôn ngữ.
- **Vì sao không dùng embedding tiếng Anh thuần**: Văn bản pháp luật VN có phân bố từ vựng và cấu trúc câu khác biệt lớn so với văn bản chung; embedding chỉ train tiếng Anh sẽ cho similarity kém chính xác trên tiếng Việt, đặc biệt với thuật ngữ hành chính-pháp lý không phổ biến trong dữ liệu train chung.
- **Vector DB đề xuất**: Qdrant hoặc Milvus — cả hai hỗ trợ HNSW index (cân bằng tốc độ/độ chính xác tốt nhất cho tập dữ liệu vừa và lớn) và hỗ trợ lọc theo metadata (payload filter) — cần thiết để lọc theo `trang_thai=hiệu lực` trước khi tính similarity.
- **Cách triển khai**:
  - Batch embed toàn bộ chunk (không real-time) bằng GPU, dùng sentence-transformers hoặc API của model.
  - Insert vào Qdrant kèm đầy đủ payload metadata (không nhúng metadata vào text để giữ vector thuần ngữ nghĩa).
  - Tạo HNSW index với tham số m=16, ef_construction=200 (điểm khởi đầu hợp lý, tinh chỉnh sau theo benchmark thực tế trên tập dữ liệu của bạn).

**[9b] Sparse Encoding → BM25/Inverted Index**
- **Mục đích**: Cho phép match chính xác từ khóa/thuật ngữ (số Điều, mã văn bản, tên riêng) mà dense embedding hay bỏ sót.
- **Công nghệ**: Elasticsearch hoặc OpenSearch (có sẵn BM25 built-in, đồng thời có thể lưu cả dense vector nếu muốn gộp một hệ thống duy nhất thay vì vận hành 2 hệ thống riêng).
- **Vì sao bắt buộc phải có, không thể chỉ dùng dense**: Câu hỏi kiểu "Điều 12 Nghị định 13/2023/NĐ-CP quy định gì" cần match chính xác chuỗi "Điều 12" và "13/2023/NĐ-CP" — dense embedding có thể xếp hạng thấp các chunk chứa đúng những từ này nếu ngữ cảnh xung quanh khác biệt, trong khi BM25 xử lý cực tốt loại truy vấn exact-match này.
- **Cách triển khai**: Index cùng lúc với bước embedding, dùng tokenizer tiếng Việt phù hợp (ví dụ `underthesea` để tách từ) trước khi đưa vào BM25 analyzer, vì tiếng Việt không phân tách từ bằng khoảng trắng đơn thuần như tiếng Anh.

**[9c] Entity/Relation Extraction → Knowledge Graph**
- **Mục đích**: Biểu diễn tường minh quan hệ liên văn bản (sửa đổi, thay thế, căn cứ, hướng dẫn thi hành) mà similarity ngữ nghĩa không nắm bắt được.
- **Công nghệ**: Rule-based cho câu dẫn chiếu theo mẫu cố định + LLM cho phần diễn đạt tự do; lưu trong Neo4j.
- **Vì sao cần Graph bên cạnh Vector DB, không thể thay thế nhau**: Hai văn bản có quan hệ sửa đổi trực tiếp có thể diễn đạt nội dung rất khác nhau (một cái ra quy định gốc, một cái chỉ nói "sửa cụm từ X thành Y") → similarity vector giữa chúng có thể thấp dù quan hệ pháp lý là trực tiếp và quan trọng nhất. Graph biểu diễn quan hệ này một cách tường minh, không phụ thuộc vào độ tương đồng nội dung.
- **Cách triển khai (giai đoạn đầu)**:
  - Node types: `VanBan`, `Dieu`. Edge types: `SUA_DOI`, `THAY_THE`, `CAN_CU`, `HUONG_DAN`, `THUOC` (Điều thuộc văn bản nào).
  - Bắt đầu chỉ với rule-based extraction từ các câu mở đầu văn bản ("Căn cứ...", "sửa đổi, bổ sung...") — phần lớn giá trị nằm ở đây, community detection và global search (GraphRAG nâng cao) nên để lại cho giai đoạn sau khi hệ thống đã ổn định.

### B. QUERY PIPELINE

**[1] Query Understanding**
- **Mục đích**: Chuẩn hóa câu hỏi, phân loại ý định, tự động suy ra metadata filter.
- **Công nghệ**: LLM nhỏ (cùng model dùng ở bước generation, hoặc một model rẻ hơn) với prompt có few-shot ép output JSON: `{"intent": "hoi_muc_phat", "filters": {"status": "hieu_luc"}, "rewritten_query": "..."}`.
- **Vì sao cần bước này thay vì đưa thẳng câu hỏi thô vào retrieval**: Câu hỏi thực tế thường khẩu ngữ, thiếu chủ ngữ, hoặc ngầm định ngữ cảnh ("vậy còn trường hợp X thì sao" — cần lịch sử hội thoại để hiểu X là gì). Nếu không rewrite, retrieval sẽ nhận một query mơ hồ và cho recall thấp.
- **Cách triển khai**: Truyền lịch sử hội thoại gần nhất (2-3 lượt) + câu hỏi hiện tại vào prompt rewriting; validate output JSON bằng schema (dùng pydantic) trước khi truyền tiếp, nếu LLM trả sai format thì fallback dùng câu hỏi gốc không rewrite.

**[2] Planner / Router**
- **Mục đích**: Quyết định bằng rule đơn giản (không cần model riêng) xem có nên bật các bước tốn thêm chi phí/latency hay không, dựa trên kết quả phân loại ở bước [1].
- **Rule cụ thể**: câu hỏi chứa số Điều/mã văn bản cụ thể → bỏ qua HyDE (ưu tiên exact-match từ khóa); câu hỏi được phân loại multi-hop/so sánh → bật Graph traversal ở bước Hybrid Retrieval; câu hỏi có nhắc "hiện hành/mới nhất" → set filter `status=effective` cho bước Metadata Filter.
- **Vì sao cần bước này**: chạy HyDE cho mọi câu hỏi vừa tốn thêm 1 lượt gọi LLM (chi phí, latency) vừa có thể **giảm** recall với câu hỏi đã đủ cụ thể (ví dụ hỏi thẳng "Điều 17 quy định gì" — HyDE sinh ra một đoạn văn giả định có thể làm loãng match từ khóa chính xác thay vì giúp ích). Planner giúp chỉ trả chi phí này khi thực sự cần.

**[3] Metadata Filter** *(đặt trước Hybrid Retrieval)*
- **Mục đích**: Lọc theo `status=effective` (và các điều kiện khác do Planner suy ra) trước khi tính similarity.
- **Vì sao đặt ở đây, không để tới bước rerank mới lọc**: lọc trước giúp tăng precision ngay từ đầu (không để văn bản hết hiệu lực lọt vào tập ứng viên) và giảm compute lãng phí (không tính similarity cho các chunk chắc chắn sẽ bị loại sau).
- **Cách triển khai**: dùng payload filter có sẵn của Vector DB (Qdrant/Milvus) và term filter của BM25 (Elasticsearch/OpenSearch) — không cần thêm hạ tầng lưu trữ metadata riêng.

**[4] Query Expansion (HyDE + Multi-query)** — chỉ chạy khi Planner ở bước [2] quyết định cần
- **Mục đích**: Tăng recall bằng cách tạo thêm các biến thể truy vấn.
  - **HyDE (Hypothetical Document Embeddings)**: Yêu cầu LLM sinh một đoạn văn giả định trả lời câu hỏi (dù có thể sai nội dung), rồi embed đoạn đó thay vì embed câu hỏi gốc.
  - **Vì sao HyDE hiệu quả**: Câu hỏi thường ngắn, khẩu ngữ; văn bản luật dài, văn phong hành chính — khoảng cách ngữ nghĩa giữa hai loại văn bản này khá lớn trong không gian embedding. Một đoạn văn giả định (dù nội dung có thể chưa đúng) có văn phong gần với văn bản luật thật hơn câu hỏi gốc, nên embedding của nó match tốt hơn với chunk thật trong index.
  - **Multi-query**: LLM sinh 2-3 cách diễn đạt khác của cùng câu hỏi (dùng từ đồng nghĩa/thuật ngữ khác) → retrieve riêng cho từng biến thể → gộp kết quả.
- **Cách triển khai**: Chạy song song (async) 1 lần gọi HyDE + 1 lần gọi multi-query, không tuần tự, để không cộng dồn latency; giới hạn multi-query tối đa 2-3 biến thể để kiểm soát chi phí.

**[5] Hybrid Retrieval**
- **Mục đích**: Lấy tập ứng viên từ cả 3 nguồn: BM25 (từ khóa chính xác), Dense (ngữ nghĩa), Graph traversal (quan hệ pháp lý tường minh, chỉ chạy khi Planner ở bước [2] bật, không chạy cho mọi câu hỏi để tiết kiệm latency).
- **Cách triển khai**: Chạy 3 truy vấn song song (async) trên tập đã qua Metadata Filter ở bước [3], mỗi nguồn trả về top-30~50 ứng viên riêng.

**[6] Reciprocal Rank Fusion (RRF)**
- **Mục đích**: Hợp nhất các danh sách kết quả có thang điểm không tương thích nhau (BM25 score và cosine similarity không cùng đơn vị).
- **Vì sao chọn RRF thay vì cộng có trọng số (weighted sum)**: Weighted sum đòi hỏi phải tune trọng số giữa BM25 score và cosine similarity — hai đại lượng có phân bố hoàn toàn khác nhau, việc tune rất dễ overfit vào tập test nhỏ; RRF chỉ dùng thứ hạng (rank), không dùng giá trị điểm số tuyệt đối, nên ổn định hơn và không cần tuning — đây là lý do RRF được dùng làm mặc định trong hầu hết hệ thống hybrid search production hiện nay (Elastic, Weaviate).
- **Công thức**: `score(d) = Σ 1 / (k + rank_i(d))` với k thường chọn = 60 (giá trị mặc định phổ biến, ít nhạy với thay đổi).

**[7] Cross-Encoder Reranker + Rule-based Boost**
- **Mục đích**: Đánh giá lại độ liên quan thực sự bằng model mạnh hơn cho top-k ứng viên sau RRF (thường lấy top 20-30), kết hợp thêm điểm rule theo hiệu lực văn bản.
- **Model đề xuất**: `BGE-reranker-v2-m3` (open-source, đa ngôn ngữ, hỗ trợ tiếng Việt).
- **Vì sao cần rerank dù đã hybrid retrieval**: Retrieval (dù hybrid) vẫn dùng biểu diễn độc lập giữa câu hỏi và document (bi-encoder/BM25) — nhanh nhưng không có tương tác trực tiếp giữa hai chuỗi. Cross-encoder encode cặp (câu hỏi, chunk) cùng lúc, bắt được tương tác tinh vi hơn, nên chính xác hơn — nhưng chậm hơn nhiều lần nên chỉ áp dụng cho tập nhỏ đã được retrieval lọc trước.
- **Công thức kết hợp (rule-based boost)**: `final_score = w1·cross_encoder_score + w2·effective_status_boost + w3·source_confidence_boost` — chunk có `trạng_thái=hết_hiệu_lực` bị trừ điểm mạnh hoặc loại hẳn (trừ khi câu hỏi hỏi rõ về "quy định cũ"). Đây là logic không thể để model tự học, cần rule tường minh vì hậu quả sai là nghiêm trọng.

**[8] Context Builder**
- **Mục đích**: Từ child chunk trúng (Khoản/Điểm) sau rerank, lấy về parent chunk đầy đủ (toàn Điều) để đưa vào prompt.
- **Vì sao cần**: retrieval/rerank hoạt động tốt nhất ở cấp granular (Khoản/Điểm) để match chính xác, nhưng LLM cần ngữ cảnh đầy đủ của cả Điều để trả lời không thiếu điều kiện áp dụng — đây chính là lý do có chiến lược parent-child ở bước Chunking.
- **Cách triển khai**: nếu câu hỏi cần thêm ngữ cảnh liên Điều (phát hiện qua Intent ở bước [1]), lấy thêm qua liên kết `prev_dieu_id`/`next_dieu_id` đã lưu ở bước Adaptive Chunking.

**[9] Prompt Builder**
- **Mục đích**: Dựng prompt gồm System Prompt, Legal Constraints, Retrieved Context, Citation Rules, Output Format, Few-shot, Question.
- **Vì sao giới hạn context 3-5 chunk, không nhồi nhiều hơn**: Hiện tượng "lost-in-the-middle" — LLM đọc kém các đoạn nằm giữa context dài, đặc biệt với LLM nhỏ (<4B tham số) có khả năng attend context dài yếu hơn LLM lớn.
- **Vì sao cần Legal Constraints tường minh**: chỉ thị "chỉ trả lời dựa trên context, không suy diễn, phải trích dẫn đúng định dạng, nếu không đủ căn cứ phải từ chối" giảm hallucination rõ rệt so với prompt chỉ có context và câu hỏi — nên nhắc lại constraint quan trọng nhất một lần nữa ngay trước câu hỏi, vì LLM nhỏ dễ "quên" chỉ thị ở đầu khi context dài.
- **Cách triển khai**: Dùng template engine (Jinja2) để tách rời logic dựng prompt khỏi nội dung, dễ A/B test các version prompt khác nhau.

**[10] LLM Router**
- **Mục đích**: chọn model phù hợp theo độ phức tạp câu hỏi (đã phân loại ở bước [1]) — câu hỏi tra cứu trực tiếp một Điều dùng model nhỏ hơn, câu hỏi cần suy luận/so sánh dùng model lớn hơn trong cùng nhóm được phép, để tiết kiệm GPU.
- **Model đề xuất**: `Gemma-2-2B-it` (đơn giản) và `Qwen2.5-3B-Instruct` (phức tạp hơn) — cả hai open-source, hỗ trợ đa ngôn ngữ khá tốt, cần đánh giá thực nghiệm trên benchmark tiếng Việt trước khi chốt.
- **Ràng buộc bắt buộc nếu mục tiêu là nộp bài cuộc thi LegalQA**: cả hai model trong router đều phải dưới 4 tỷ tham số, mã nguồn mở, và đã đăng ký với ban tổ chức — **không dùng model 7B trở lên** như một số gợi ý production tổng quát, vì sẽ vi phạm quy chế cuộc thi. Nếu hệ thống phục vụ mục tiêu production hoàn toàn ngoài phạm vi cuộc thi thì ràng buộc này không áp dụng.
- **Vì sao cân nhắc fine-tune LoRA**: LLM nhỏ chưa được train nhiều trên dữ liệu pháp lý tiếng Việt, dễ trả lời chung chung hoặc sai định dạng trích dẫn; fine-tune nhẹ (LoRA/QLoRA) trên vài nghìn cặp (câu hỏi, context, câu trả lời chuẩn) cải thiện đáng kể độ ổn định mà chi phí thấp.
- **Serving**: Dùng vLLM để tận dụng continuous batching, giảm chi phí và tăng throughput khi có nhiều request đồng thời.

**[11] Groundedness Check**
- **Mục đích**: Kiểm tra **nội dung** câu trả lời có thực sự được context hỗ trợ hay không — đây là lớp chống hallucination cấp ý nghĩa (khác với bước [12] kiểm tra cấp số liệu trích dẫn).
- **Cách triển khai (2 lựa chọn, có thể kết hợp)**:
  - NLI-based: Dùng model entailment đánh giá quan hệ giữa từng câu trả lời và context — nhãn "entailment" thì giữ, "contradiction"/"neutral" thì đánh dấu nghi ngờ.
  - LLM-as-judge: Gọi lại LLM với câu hỏi "câu trả lời sau có được đoạn văn bản này hỗ trợ trực tiếp không, trả lời có/không kèm câu trích chứng minh".

**[12] Citation Verification** 
- **Mục đích**: Kiểm tra số Điều/Khoản/tên văn bản mà LLM trích dẫn có khớp **chính xác** với chunk thực sự dùng để sinh câu đó không.
- **Vì sao phải tách riêng khỏi Groundedness Check ở [11]**: đây là hai loại lỗi độc lập. LLM có thể trả lời **đúng nội dung** nhưng **bịa nhầm số Điều** — ví dụ nói "Điều 128" trong khi chunk thực tế đưa vào prompt là "Điều 127". Groundedness Check ở mức ý nghĩa không bắt được lỗi số liệu này, cần một bước match string/id tường minh riêng.
- **Cách triển khai**: với mỗi trích dẫn LLM sinh ra, so khớp trực tiếp với `document_id`/`dieu_so`/`khoan_so` của (các) chunk đã đưa vào prompt (lưu lại từ bước Context Builder) — nếu không khớp, reject và yêu cầu sinh lại hoặc trả về "không đủ căn cứ".

**[13] Hallucination Detection**
- **Mục đích**: Tổng hợp nhãn từ [11] và [12] thành một mức rủi ro duy nhất (thấp/trung bình/cao).
- **Nếu không đạt (rủi ro cao ở một trong hai hoặc cả hai bước)**: Không trả lời liều — trả về *"hệ thống không tìm đủ căn cứ rõ ràng để trả lời chính xác câu hỏi này"* thay vì đoán, vì chi phí của một câu trả lời sai trong domain pháp lý cao hơn nhiều so với việc từ chối trả lời.

**Citation Formatting** *(gộp cùng bước [12]-[13])*
- Map câu trả lời đã pass toàn bộ kiểm tra sang định dạng chuẩn `[Điều X, Khoản Y — Tên văn bản, số hiệu]`, dựa trên metadata đã gắn từ chunking ở Document Pipeline.

**[14] Confidence Scoring**
- **Mục đích**: Cho người dùng biết mức độ tin cậy của câu trả lời để họ biết khi nào nên tra cứu thêm.
- **Công thức đa nguồn**: `confidence = f(retriever_score, cross_encoder_score, groundedness_pass, citation_match, source_agreement)` — quy về thang dễ hiểu (Cao/Trung bình/Thấp).
- **Vì sao không dùng LLM tự báo %**: độ tin cậy tự báo của LLM được nhiều nghiên cứu về calibration chỉ ra là không phản ánh đúng xác suất chính xác thực tế — kết hợp tín hiệu từ nhiều bước trong pipeline (retrieval, rerank, groundedness, citation match) đáng tin hơn nhiều so với việc hỏi thẳng LLM "bạn tự tin bao nhiêu %".

---

## C. OPS LAYER

**[1] Incremental Indexing**
- Kích hoạt tự động khi phát hiện văn bản mới/sửa đổi (cron job hoặc trigger từ nguồn dữ liệu chính thức); đánh dấu chunk cũ là outdated (không xóa, giữ để trả lời câu hỏi về quy định cũ khi được hỏi rõ), chạy lại Version Linking để cập nhật Version Graph.

**[2] Evaluation — vòng lặp liên tục**
- `Answer → Evaluation (so với tập câu hỏi chuẩn + feedback đã duyệt) → Log → Error Analysis (phân loại: lỗi retrieval / lỗi citation / lỗi suy luận) → cập nhật Retriever hoặc Prompt tương ứng theo đúng loại lỗi.`
- Dùng framework kiểu RAGAS làm tham khảo cho các chỉ số cần đo (recall@k, faithfulness, answer relevance), có thể tự triển khai đơn giản hơn.

**[3] Monitoring — metric cụ thể cần theo dõi**
- Latency (p50/p95), GPU utilization, Recall@k của retrieval, Precision của rerank, Hallucination rate (từ bước [13]), tỉ lệ "không đủ căn cứ", danh sách failure case để review định kỳ.

**[4] Cache — 3 lớp riêng biệt**
- Semantic Cache: câu trả lời cuối cho câu hỏi ngữ nghĩa giống nhau (dựa trên similarity của câu hỏi đã chuẩn hóa).
- Retriever Cache: kết quả retrieval cho cùng một query đã rewrite (tránh chạy lại hybrid search).
- LLM Cache: theo prompt hash chính xác (khi prompt giống hệt, không cần gọi lại LLM).

**[5] Feedback Loop — có lớp kiểm duyệt chuyên môn**
- `User 👍👎 → Hàng chờ review → Chuyên gia pháp lý xác nhận đúng/sai → chỉ dữ liệu đã xác nhận vào Dataset → Evaluation → Fine-tune.`
- **Vì sao không dùng feedback thô trực tiếp**: người dùng phổ thông không phải lúc nào cũng biết câu trả lời pháp lý đúng hay sai để bấm 👍/👎 chính xác — đưa thẳng vào vòng fine-tune có rủi ro khuếch đại lỗi thay vì sửa lỗi trong domain đòi hỏi độ chính xác cao.

**[6] Security**
- Input sanitization (chống prompt injection nếu tương lai cho phép người dùng upload văn bản), kiểm soát PII trong log theo quy định về bảo vệ dữ liệu cá nhân.

---

## CẤP 4 — Lộ trình triển khai production (roadmap theo giai đoạn)

Không nên xây toàn bộ kiến trúc trên cùng một lúc. Thứ tự dưới đây ưu tiên theo mức độ ảnh hưởng đến độ chính xác câu trả lời trước, độ hoàn thiện vận hành sau.

### Giai đoạn 1 — MVP nền tảng đúng
- **Mục tiêu**: Pipeline chạy được end-to-end với chất lượng chunking/metadata đúng ngay từ đầu, vì sai ở đây thì mọi cải tiến sau đều vô nghĩa.
- **Triển khai**:
  - `[1] Ingest & Extract Text` → `[2] Layout Analysis` → `[3] Legal Structure Parsing` → `[4] Cleaning` → `[5] Citation Extraction` → `[6] Metadata Extraction` → `[7] Version Linking` → `[8] Adaptive Legal Chunking`.
  - `[9a] Dense Embedding` + `Vector DB` (chỉ dense, chưa cần hybrid ngay).
  - Query Pipeline tối giản: câu hỏi thô → dense retrieval → rerank → prompt → LLM → trả lời (chưa có Groundedness/Citation Verification).
- **Vì sao bắt đầu từ đây**: Đây là phần quyết định phần lớn chất lượng cuối cùng; làm sai chunking/metadata/version linking ở giai đoạn này thì các giai đoạn sau (hybrid, graph, groundedness) chỉ tối ưu trên một nền tảng sai.

### Giai đoạn 2 — Nâng độ chính xác retrieval và chống hallucination
- **Mục tiêu**: Đây là nhóm rủi ro cao nhất trong domain pháp lý — trả lời sai hoặc bịa căn cứ.
- **Triển khai**:
  - Thêm `[9b] Sparse/BM25` + `[5] Hybrid Retrieval` + `[6] Reciprocal Rank Fusion`.
  - Thêm `[3] Metadata Filter` trước retrieval (lọc `status=effective`).
  - Thêm rule-based boost theo hiệu lực ở `[7] Cross-Encoder Reranker`.
  - Thêm `[11] Groundedness Check` + `[12] Citation Verification` + `[13] Hallucination Detection` (ba bước tách riêng, không gộp).
  - Thêm `[14] Confidence Scoring` đa nguồn.
- **Vì sao ưu tiên trước Graph**: Hybrid retrieval và chống hallucination cải thiện trực tiếp độ chính xác của mọi câu hỏi, trong khi Graph chỉ giúp với nhóm câu hỏi multi-hop/so sánh — ROI (hiệu quả trên công sức bỏ ra) của giai đoạn này cao hơn.

### Giai đoạn 3 — Truy vấn thông minh & GraphRAG cho câu hỏi phức tạp
- **Mục tiêu**: Xử lý tốt câu hỏi cần quan hệ liên văn bản (sửa đổi, thay thế, dẫn chiếu), câu hỏi khẩu ngữ/mơ hồ, và tiết kiệm GPU.
- **Triển khai**:
  - Thêm `[9c] Entity/Relation Extraction` + Knowledge Graph (gộp cả Version Graph, bắt đầu rule-based, không cần community detection ngay).
  - Nâng cấp `[1] Query Understanding` đầy đủ (Spell Correction, Legal Entity Recognition) và `[2] Planner/Router` để quyết định khi nào bật HyDE/Graph traversal.
  - Thêm `[10] LLM Router` — lưu ý cả hai model trong router phải dưới 4B nếu mục tiêu là nộp bài cuộc thi.

### Giai đoạn 4 — Production hardening
- **Mục tiêu**: Hệ thống vận hành ổn định lâu dài, không chỉ "chạy đúng lúc demo".
- **Triển khai**:
  - **Incremental Indexing**: Pipeline tự động phát hiện văn bản mới/sửa đổi (cron job hoặc trigger từ nguồn dữ liệu chính thức), đánh dấu chunk cũ là outdated thay vì xóa.
  - **Evaluation Pipeline**: Xây bộ câu hỏi kiểm thử có đáp án chuẩn, đo recall@k, faithfulness, answer relevance.
  - **Monitoring & Logging**: Log đầy đủ query → chunk retrieved → prompt → answer → confidence.
  - **Cache 3 lớp**: Bổ sung Semantic Cache, Retriever Cache và LLM Cache để tối ưu chi phí và độ trễ.
  - **Feedback Loop**: Áp dụng cơ chế kiểm duyệt chuyên môn (human-in-the-loop) để làm sạch dữ liệu trước khi fine-tune.
  - **Security**: Input sanitization và kiểm soát PII.
