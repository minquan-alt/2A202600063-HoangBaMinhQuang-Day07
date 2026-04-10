# Báo Cáo Lab 7: Embedding & Vector Store

**Họ tên:** Hoàng Bá Minh Quang
**Nhóm:** C401-A2
**Ngày:** 10/04/2026
---

## 1. Warm-up (5 điểm)

### Cosine Similarity (Ex 1.1)

**High cosine similarity nghĩa là gì?**
- High cosine similarity nghĩa là hai vector (thường là embedding của câu/văn bản) có hướng rất giống nhau, thể hiện mức độ tương đồng ngữ nghĩa cao giữa chúng.

**Ví dụ HIGH similarity:**
- Sentence A: Chị trợ giảng xinh quá
- Sentence B: Chị phụ tá đẹp quá
- Tại sao tương đồng: Hai câu có ý nghĩa gần như giống nhau vì “trợ giảng” và “phụ tá” đều chỉ vai trò hỗ trợ, còn “xinh” và “đẹp” là các từ đồng nghĩa, nên embedding của hai câu có hướng rất gần nhau (cosine similarity cao).

**Ví dụ LOW similarity:**
- Sentence A: 2 con chó chơi đùa với nhau
- Sentence B: Em muốn đi học
- Tại sao khác: 2 chủ ngữ không liên quan gì đến nhau, 2 hoạt động cũng không liên quan gì đến nhau

**Tại sao cosine similarity được ưu tiên hơn Euclidean distance cho text embeddings?**
Cosine similarity được ưu tiên vì nó đo độ tương đồng về hướng của vector (ngữ nghĩa), không bị ảnh hưởng bởi độ dài vector. Trong khi đó, Euclidean distance phụ thuộc vào độ lớn vector nên kém hiệu quả hơn trong việc so sánh ngữ nghĩa giữa các embedding.

### Chunking Math (Ex 1.2)

**Document 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> *Trình bày phép tính:*
Step = chunk_size – overlap = 500 – 50 = 450
Số chunks ≈ ⌈(Document length – overlap) / Step⌉
= ⌈(10,000 – 50) / 450⌉
= ⌈9,950 / 450⌉ ≈ ⌈22.11⌉ = 23
> *Đáp án:* 
23
**Nếu overlap tăng lên 100, chunk count thay đổi thế nào? Tại sao muốn overlap nhiều hơn?**
Khi overlap tăng lên 100 thì step giảm (500 – 100 = 400), nên số chunks tăng lên (≈ ⌈(10,000 – 100)/400⌉ = 25 chunks). Overlap lớn hơn giúp giữ được ngữ cảnh giữa các chunk, tránh mất thông tin ở ranh giới khi retrieval.
---

## 2. Document Selection — Nhóm (10 điểm)

### Domain & Lý Do Chọn

**Domain:** Hybrid retrieval benchmark (5 tài liệu nội bộ mẫu của giảng viên + 1 tài liệu OCR về hướng dẫn nấu ăn do cá nhân crawl/xử lý).

**Tại sao nhóm chọn domain này?**
Nhóm dùng 5 tài liệu có sẵn của giảng viên làm baseline để so sánh chunking và retrieval ổn định. Đồng thời, nhóm bổ sung 1 tài liệu OCR do cá nhân tự thu thập để kiểm tra độ bền của pipeline khi gặp dữ liệu nhiễu và cấu trúc không đồng nhất. Cách chọn này giúp đánh giá rõ hiệu quả metadata/filter trong cả điều kiện “sạch” và “thực tế”.

### Data Inventory

| #   | Tên tài liệu                  | Nguồn                              | Số ký tự | Metadata đã gán                                         |
| --- | ----------------------------- | ---------------------------------- | -------- | ------------------------------------------------------- |
| 1   | customer_support_playbook.txt | data/customer_support_playbook.txt | 1692     | source, extension, doc_type, department, language       |
| 2   | rag_system_design.md          | data/rag_system_design.md          | 2391     | source, extension, doc_type, department, language       |
| 3   | vector_store_notes.md         | data/vector_store_notes.md         | 2123     | source, extension, doc_type, department, language       |
| 4   | vi_retrieval_notes.md         | data/vi_retrieval_notes.md         | 1667     | source, extension, doc_type, department, language       |
| 5   | chunking_experiment_report.md | data/chunking_experiment_report.md | 1987     | source, extension, doc_type, department, language       |
| 6   | huong_dan_nau_an.md           | data/huong_dan_nau_an.md           | 195560   | source, doc_type, department, language, domain, cuisine |

### Metadata Schema

| Trường metadata | Kiểu   | Ví dụ giá trị                 | Tại sao hữu ích cho retrieval?                 |
| --------------- | ------ | ----------------------------- | ---------------------------------------------- |
| cuisine         | string | Vietnamese                    | Hữu ích cho retrieval món ăn                   |
| source          | str    | rag_system_design.md          | Truy vết nguồn chunk sau khi retrieve          |
| doc_type        | str    | playbook / notes / design_doc | Lọc theo loại tài liệu cho đúng ngữ cảnh       |
| department      | str    | support / platform            | Giảm nhiễu khi query theo team                 |
| language        | str    | vi / en                       | Tránh lấy sai ngôn ngữ khi câu hỏi có scope rõ |
| domain          | str    | cooking / ai / system_design  | Phân nhóm theo lĩnh vực                        |
---

## 3. Chunking Strategy — Cá nhân chọn, nhóm so sánh (15 điểm)

### Baseline Analysis

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

| Tài liệu | Strategy | Chunk Count | Avg Length | Preserves Context? |
|-----------|----------|-------------|------------|-------------------|
| customer_support_playbook.txt | FixedSizeChunker (`fixed_size`) | 9 | 207.56 | Trung bình |
| customer_support_playbook.txt | SentenceChunker (`by_sentences`) | 4 | 421.00 | Khá tốt nhưng chunk dài |
| customer_support_playbook.txt | RecursiveChunker (`recursive`) | 13 | 128.31 | Tốt |
| rag_system_design.md | FixedSizeChunker (`fixed_size`) | 12 | 219.42 | Trung bình |
| rag_system_design.md | SentenceChunker (`by_sentences`) | 5 | 476.00 | Tốt nhưng quá dài |
| rag_system_design.md | RecursiveChunker (`recursive`) | 20 | 117.65 | Tốt |
| vi_retrieval_notes.md | FixedSizeChunker (`fixed_size`) | 9 | 204.78 | Trung bình |
| vi_retrieval_notes.md | SentenceChunker (`by_sentences`) | 5 | 331.60 | Khá tốt |
| vi_retrieval_notes.md | RecursiveChunker (`recursive`) | 12 | 137.00 | Tốt |
| huong_dan_nau_an.md | FixedSizeChunker (`fixed_size`) | 978 | 219.89 | Trung bình |
| huong_dan_nau_an.md | SentenceChunker (`by_sentences`) | 758 | 253.62 | Khá tốt |
| huong_dan_nau_an.md | RecursiveChunker (`recursive`) | 1245 | 153.85 | Tốt |

### Strategy Của Tôi

**Loại:** RecursiveChunker

**Mô tả cách hoạt động:**
Mình dùng chiến lược tách đệ quy theo mức ưu tiên separator: đoạn trống lớn, xuống dòng, dấu chấm, khoảng trắng, rồi fallback fixed-size. Ý tưởng là ưu tiên giữ các biên ngữ nghĩa lớn trước, chỉ tách nhỏ khi chunk vượt giới hạn. Cách này giúp chunk ngắn vừa đủ cho embedding nhưng vẫn giữ được cụm ý tương đối trọn vẹn. Với tài liệu notes/playbook, kết quả chunk thường dễ đọc và truy xuất ổn định hơn.

**Tại sao tôi chọn strategy này cho domain nhóm?**
Domain nhóm có tài liệu hỗn hợp: có chỗ viết thành đoạn dài, có chỗ dạng bullet/heading. Recursive chunking tận dụng được cấu trúc đó vì nó ưu tiên tách theo khối trước rồi mới cắt nhỏ hơn. Vì vậy chunk ít bị đứt ý hơn so với cắt cố định ngay từ đầu.

**Code snippet (nếu custom):**
Không dùng custom strategy riêng, mình dùng implementation `RecursiveChunker` trong `src/chunking.py`.

### So Sánh: Strategy của tôi vs Baseline

| Tài liệu | Strategy | Chunk Count | Avg Length | Retrieval Quality? |
|-----------|----------|-------------|------------|--------------------|
| huong_dan_nau_an.md | SentenceChunker (best baseline dễ đọc) | 758 | 253.62 | Khá (top-1 avg score: 0.8615) |
| huong_dan_nau_an.md | **RecursiveChunker (của tôi)** | 1245 | 153.85 | Tốt và ổn định hơn (top-1 avg score: 0.8669) |

### So Sánh Với Thành Viên Khác

| Thành viên | Strategy | Retrieval Score (/10) | Điểm mạnh | Điểm yếu |
|-----------|----------|----------------------|-----------|----------|
| Tôi | RecursiveChunker | 8.0 | Cân bằng giữa độ ngắn chunk và giữ ngữ cảnh | Nhiều chunk hơn, tốn index hơn |
| Nguyễn Anh Tài        | RecipeChunker (Custom) | 8/10                  | Giữ trọn vẹn ngữ cảnh từng bước nấu; lọc nhiễu tốt nhờ tách biệt tiêu đề và nội dung. | Số lượng chunk lớn làm tăng thời gian nhúng (embedding) và tìm kiếm ban đầu. |
| Trần Quang Long | RecursiveChunker | 10/10 | giữ trọn vẹn danh sách nguyên liệu hoặc trọn vẹn một bước nấu ăn trong cùng một chunk | Không có điểm yếu |
| Nguyễn Công Quốc Huy        | SectionChunker(Custom) | 8/10                | Đưa ra chính xác section cần | Số lượng chunk tương đối làm tăng thời gian nhúng (embedding) và tìm kiếm ban đầu.
| Vũ Minh Quân         | RecursiveChunker       | 8/10                  | giữ cửa sổ ngữ cảnh, tránh bị loãng thông tin                                         | nhiều chunk gây tốn thời gian trích xuất và tìm kiếm                                 |
| Đỗ Lê Thành Nhân     | SentenceChunker        | 7/10                  | Đảm bảo tính toàn vẹn về mặt ngữ nghĩa của từng câu đơn lẻ.                           | AI khó liên kết giữa nguyên liệu và hành động nấu nếu chúng nằm ở các câu khác nhau. |

**Strategy nào tốt nhất cho domain này? Tại sao?**
Ở thời điểm hiện tại, RecursiveChunker là lựa chọn tốt nhất cho bộ dữ liệu của nhóm mình. Lý do là tài liệu có cấu trúc không đồng nhất, nên tách theo nhiều cấp separator giúp cân bằng giữa coherence và độ dài chunk. Tuy nhiên phần so sánh cuối cùng vẫn cần thêm kết quả chạy của các thành viên còn lại.

---

## 4. My Approach — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi implement các phần chính trong package `src`.

### Chunking Functions

**`SentenceChunker.chunk`** — approach:
Mình dùng regex `(?<=[.!?])\s+` để tách câu theo dấu `.`, `!`, `?` kết hợp khoảng trắng sau dấu câu. Sau đó gom lại theo `max_sentences_per_chunk`, đủ số câu thì tạo chunk mới. Edge case chính là văn bản rỗng hoặc ít câu thì trả về ít chunk tương ứng, không phát sinh lỗi.

**`RecursiveChunker.chunk` / `_split`** — approach:
`chunk()` gọi `_split()` với danh sách separator ưu tiên từ lớn đến nhỏ. Base case là khi chiều dài đoạn hiện tại <= `chunk_size` thì trả luôn, hoặc hết separator thì fallback sang `FixedSizeChunker` overlap 0. Khi tách, mình gom `parts` vào buffer để hạn chế tạo chunk quá ngắn và chỉ đệ quy sâu hơn nếu đoạn vẫn vượt ngưỡng.

### EmbeddingStore

**`add_documents` + `search`** — approach:
Mình thiết kế store theo hướng ưu tiên qdrant nếu cấu hình được, nếu không thì fallback sang in-memory list. Với các file thường, metadata giữ gọn theo `source` và `extension` như luồng ban đầu. Riêng `huong_dan_nau_an.md` (dữ liệu OCR), mình bổ sung thêm metadata mở rộng như `doc_type`, `language`, `line_count`, `digit_only_line_ratio`, `short_line_ratio`, `ocr_noise_level` để dễ lọc và đánh giá chất lượng retrieval. Khi search in-memory, mình embed query rồi tính dot product với toàn bộ vector đã lưu, sau đó sort giảm dần theo score.

**`search_with_filter` + `delete_document`** — approach:
`search_with_filter()` filter metadata trước, rồi mới chạy similarity trên tập đã lọc để tăng precision. `delete_document()` xóa tất cả chunk có `doc_id` tương ứng trong in-memory store, đồng thời cố gắng xóa bên qdrant nếu đang dùng backend đó. Hàm trả về bool để biết có xóa được dữ liệu hay không.

### KnowledgeBaseAgent

**`answer`** — approach:
`answer()` lấy top-k chunk từ store trước, sau đó format thành từng dòng context có kèm score. Prompt gồm role instruction, phần Context, phần Question và cuối cùng là `Answer:` để LLM sinh trả lời. Cách này buộc câu trả lời bám vào evidence đã retrieve thay vì trả lời tự do.

### Test Results

```
============================= test session starts ==============================
platform linux -- Python 3.10.20, pytest-9.0.2
collected 42 items

tests/test_solution.py ..........................................        [100%]

============================== 42 passed in 0.05s ==============================
```

**Số tests pass:** 42 / 42

---

## 5. Similarity Predictions — Cá nhân (5 điểm)

| Pair | Sentence A | Sentence B | Dự đoán | Actual Score | Đúng? |
|------|-----------|-----------|---------|--------------|-------|
| 1 | Chị trợ giảng xinh quá | Chị phụ tá đẹp quá | high | 0.2020 | Đúng |
| 2 | 2 con chó chơi đùa với nhau | Em muốn đi học | low | -0.0750 | Đúng |
| 3 | How do I reset my password? | What is the password recovery process? | high | -0.1007 | Sai |
| 4 | Vector store supports semantic search | Embeddings are stored for similarity retrieval | high | 0.1717 | Đúng |
| 5 | I need deployment steps for billing API | Cách nấu canh chua cá lóc ngon | low | -0.0192 | Đúng |

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn nghĩa?**
Pair số 3 là kết quả bất ngờ nhất vì hai câu gần nghĩa nhưng score lại âm. Lý do là phần benchmark này mình chạy với `_mock_embed` (deterministic fallback), nên điểm không phản ánh ngữ nghĩa thật như model embedding thực tế. Điều này cho thấy đánh giá semantic cần dùng embedder thật nếu muốn kết luận chất lượng retrieval.

---

## 6. Results — Cá nhân (10 điểm)

Chạy 5 benchmark queries của nhóm trên implementation cá nhân của bạn trong package `src`. **5 queries phải trùng với các thành viên cùng nhóm.**

### Benchmark Queries & Gold Answers (nhóm thống nhất)

| # | Query | Gold Answer |
|---|-------|-------------|
| 1   | Các nguyên liệu cần thiết để làm món "Cá ngừ hấp cải rổ" là gì?                  | 1 hộp cá ngừ ngâm dầu, 300g cải rổ, muối, tiêu, đường, nước tương, dầu ăn, tỏi, hành lá, rau mùi và bánh mì |
| 2   | Quy trình thực hiện món "Chả trứng hấp" gồm những bước nào?                      | 1. Trộn tất cả nguyên liệu (trứng, thịt xay, nấm mèo, miến). 2. Hấp chín. 3. Phết lòng đỏ lên mặt.          |
| 3   | Những món ăn nào trong tài liệu sử dụng "nước dừa tươi" làm nguyên liệu?         | Bún tôm – thịt luộc (luộc thịt và pha mắm), Thịt kho tàu (nước dừa tươi), Bò kho (nước dừa tươi)            |
| 4   | Món "Gỏi cuốn" được mô tả như thế nào và thưởng thức kèm với loại nước chấm nào? | Mô tả là món cuốn tươi mát, dễ ăn. Thưởng thức bằng cách chấm tương đen hoặc nước mắm tỏi ớt                |
| 5   | Cách sơ chế và ướp cá trong món "Cá lóc kho tộ" được hướng dẫn ra sao?           | Cá lóc cắt khoanh, ướp với nước mắm, đường, tiêu, hành tím và nước màu trong 20 phút.                       |

### Kết Quả Của Tôi

| # | Query | Top-1 Retrieved Chunk (tóm tắt) | Score | Relevant? | Agent Answer (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Các nguyên liệu cần thiết để làm món "Cá ngừ hấp cải rổ" là gì? | Top-1 lấy đúng chunk nguyên liệu trong `huong_dan_nau_an.md` (1 hộp cá ngừ, cải rổ, gia vị...) | 0.8898 | Yes | Agent bám được đúng context món cần hỏi, nội dung trả lời sát phần nguyên liệu |
| 2 | Quy trình thực hiện món "Chả trứng hấp" gồm những bước nào? | Top-1 chứa trực tiếp các bước trộn nguyên liệu, hấp và hoàn thiện mặt trứng trong `huong_dan_nau_an.md` | 0.8600 | Yes | Agent trả lời đúng quy trình chính của món chả trứng hấp |
| 3 | Những món ăn nào trong tài liệu sử dụng "nước dừa tươi" làm nguyên liệu? | Top-1/top-3 truy hồi được các đoạn có dùng nước dừa/nước cốt dừa trong `huong_dan_nau_an.md` | 0.8364 | Yes (top-3) | Agent trả lời đúng hướng về nhóm món dùng nước dừa, cần hậu xử lý thêm để list tên món đầy đủ |
| 4 | Món "Gỏi cuốn" được mô tả như thế nào và thưởng thức kèm với loại nước chấm nào? | Top-1 lấy đúng chunk mô tả cách cuốn và đoạn nước chấm đi kèm trong `huong_dan_nau_an.md` | 0.8387 | Yes | Agent trả lời đúng mô tả món và cách thưởng thức với nước chấm |
| 5 | Cách sơ chế và ướp cá trong món "Cá lóc kho tộ" được hướng dẫn ra sao? | Top-1/top-3 truy hồi các đoạn sơ chế và ướp cá lóc trong `huong_dan_nau_an.md` (làm sạch, ướp gia vị, thời gian ướp) | 0.8658 | Yes (top-3) | Agent trả lời đúng các ý chính về sơ chế và ướp cá, cần kiểm soát chặt hơn để tránh lẫn biến thể món |

**Bao nhiêu queries trả về chunk relevant trong top-3?** 5 / 5

---

## 7. What I Learned (5 điểm — Demo)

**Điều hay nhất tôi học được từ thành viên khác trong nhóm:**
Mình học được từ các bạn là với dữ liệu công thức nấu ăn thì chunk phải giữ trọn ngữ cảnh theo bước hoặc theo section, nếu cắt không khéo sẽ lẫn nguyên liệu với cách làm. Khi kết hợp với metadata theo domain/language thì kết quả search ổn định hơn rõ rệt. Đây là điểm giúp nhóm mình thống nhất được hướng chunking phù hợp cho tài liệu OCR.

**Điều hay nhất tôi học được từ nhóm khác (qua demo):**
Điều mình học được từ nhóm khác là phải đo retrieval bằng benchmark cố định và rerun sau mỗi thay đổi kỹ thuật, không đoán theo cảm giác. Cách họ ghi lại trước/sau khi đổi embedding giúp nhìn ra tác động thật sự của từng tối ưu. Mình áp dụng lại cách này khi đổi sang local embedding mạnh hơn và thấy chất lượng top-k cải thiện rõ.

**Nếu làm lại, tôi sẽ thay đổi gì trong data strategy?**
Nếu làm lại, mình sẽ chuẩn hóa dữ liệu OCR kỹ hơn trước khi index (gộp dòng bị vỡ, loại bớt nhiễu số trang/mục lục), đồng thời chuẩn bị metadata ngay từ đầu theo mục tiêu truy vấn. Ngoài ra, với họ model E5 mình sẽ giữ nhất quán prefix `query:` và `passage:` trong toàn bộ pipeline để tối ưu retrieval. Sau cùng, mình sẽ thêm bước hậu xử lý để trích xuất tên món/nhóm nguyên liệu rõ ràng hơn từ các chunk top-k.

---

## Tự Đánh Giá

| Tiêu chí | Loại | Điểm tự đánh giá |
|----------|------|-------------------|
| Warm-up | Cá nhân | 5 / 5 |
| Document selection | Nhóm | 10 / 10 |
| Chunking strategy | Nhóm | 15 / 15 |
| My approach | Cá nhân | 10 / 10 |
| Similarity predictions | Cá nhân | 5 / 5 |
| Results | Cá nhân | 10 / 10 |
| Core implementation (tests) | Cá nhân | 30 / 30 |
| Demo | Nhóm | 5 / 5 |
| **Tổng** | | **100 / 100** |


