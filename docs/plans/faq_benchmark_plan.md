# Kế hoạch nâng cấp benchmark/evaluation cho eGov-Bot bằng FAQ từ dichvucong.gov.vn

## 0. Mục tiêu

Mục tiêu của kế hoạch này là nâng cấp project `eGov-Bot` từ mức “RAG chatbot demo” thành project có benchmark rõ ràng, có test data thực tế và có report đủ tốt để ghi vào CV.

Nguồn test data chính: các trang “Câu hỏi thường gặp” trên Cổng Dịch vụ công Quốc gia.

Ví dụ một trang detail có cấu trúc:

```text
Question: Cá nhân đăng ký Bồi dưỡng nghiệp vụ đăng kiểm viên tàu cá phải nộp những loại giấy tờ gì?
Answer: Theo quy định tại Khoản 3, Điều 8 Thông tư số 23/2018/TT-BNNPTNT ... gồm 3 loại giấy tờ.
Related procedure: Cấp, cấp lại thẻ, dấu kỹ thuật đăng kiểm viên tàu cá
```

Final testset dùng để đánh giá chỉ cần 3 field:

```json
{
  "question": "...",
  "reference_answer": "...",
  "expected_procedure_title": "..."
}
```

Không cần dùng `source_url`, `faq_url`, `category`, `difficulty`, `audience` trong file testset cuối. Tuy nhiên trong quá trình crawl/clean có thể lưu file raw có thêm `faq_id`, `url`, `crawl_time` để debug. File raw không dùng trực tiếp cho benchmark.

---

## 1. Vấn đề hiện tại cần sửa

Repo hiện tại đã có nền khá tốt:

- Flask web UI.
- Hybrid retrieval gồm FAISS dense search, BM25 sparse search và keyword fallback.
- Gemini answer generation có source cards.
- Docker/Docker Compose.
- SQLite logging/feedback.
- Evaluation scripts cơ bản.

Nhưng phần benchmark hiện tại còn yếu ở các điểm sau:

### 1.1 Testset hiện tại còn tự sinh bằng template

Script hiện tại kiểu:

```text
Thủ tục {title} cần hồ sơ gì?
Cơ quan nào thực hiện {title}?
Trình tự thực hiện {title} như thế nào?
Điều kiện thực hiện {title} là gì?
```

Vấn đề:

- Câu hỏi quá sạch.
- Câu hỏi luôn chứa nguyên tên thủ tục.
- Không giống người dùng thật.
- Nếu retrieval tốt trên testset này thì chưa chứng minh hệ thống tốt với câu hỏi tự nhiên.

### 1.2 Retrieval eval đang dựa vào URL

Current evaluation đang dùng `expected_url` để kiểm tra source match.

Cần chuyển sang kiểm tra bằng:

```text
expected_procedure_title
```

Lý do:

- User muốn schema gọn.
- Trong benchmark này ta chỉ cần biết retriever có tìm đúng thủ tục không.
- Title dễ đọc và dễ giải thích trong report/CV.

### 1.3 Generation eval chưa đo đúng/sai nội dung

Current generation eval chủ yếu đo:

- HTTP success rate.
- Source URL match.
- Latency.
- Answer length.

Cần bổ sung đánh giá:

- Câu trả lời có đúng với `reference_answer` không.
- Có thiếu ý quan trọng không.
- Có bịa thêm thông tin không.
- Có bám đúng thủ tục được retrieve không.

---

## 2. Thiết kế benchmark mới

Ta chia benchmark thành 3 lớp.

### 2.1 Benchmark A — Retrieval Title Matching

Input:

```json
{"question":"...","reference_answer":"...","expected_procedure_title":"..."}
```

Process:

1. Đưa `question` vào retriever.
2. Lấy top-k kết quả.
3. Lấy title của từng result.
4. So sánh normalized result title với normalized `expected_procedure_title`.

Metrics:

```text
Recall@1
Recall@3
Recall@5
Recall@10
MRR@10
nDCG@10
```

Mục tiêu:

```text
Bot có tìm đúng thủ tục liên quan đến câu hỏi FAQ không?
```

### 2.2 Benchmark B — End-to-End Answer Quality

Input:

```json
{"question":"...","reference_answer":"...","expected_procedure_title":"..."}
```

Process:

1. Gọi API `/chat` với `question`.
2. Lưu response answer, sources, latency.
3. Kiểm tra source title match.
4. Dùng LLM-as-judge để chấm answer so với `reference_answer`.

Metrics:

```text
success_rate
source_title_match@k
answer_correctness_avg, thang 1-5
faithfulness_avg, thang 1-5
missing_info_rate
hallucination_rate
pass_rate
latency_p50_ms
latency_p95_ms
```

Pass/fail gợi ý:

```text
PASS nếu:
- correctness_score >= 4
- faithfulness_score >= 4
- hallucination = false
```

### 2.3 Benchmark C — Ablation Retrieval

So sánh các mode retrieval:

```text
BM25 only
FAISS/dense only
Hybrid BM25 + FAISS
Hybrid + keyword fallback
Hybrid + reranker, nếu có làm thêm
```

Bảng report mong muốn:

| Method | Recall@1 | Recall@3 | Recall@5 | MRR@10 | nDCG@10 | Avg latency ms |
|---|---:|---:|---:|---:|---:|---:|
| BM25 only | x | x | x | x | x | x |
| Dense only | x | x | x | x | x | x |
| Hybrid | x | x | x | x | x | x |

Mục tiêu:

```text
Chứng minh thiết kế hybrid retrieval có ý nghĩa, không chỉ nói suông.
```

---

## 3. Cấu trúc thư mục đề xuất

Thêm/sửa các file như sau:

```text
evaluation/
  crawlers/
    crawl_dvc_faq_ids.py
    parse_dvc_faq_detail.py

  testsets/
    dvc_faq_raw.jsonl
    dvc_faq_clean_full.jsonl
    dvc_faq_qa_300.jsonl
    dvc_faq_qa_500.jsonl
    dvc_faq_manual_review.csv

  utils/
    text_normalize.py
    title_matching.py
    jsonl_io.py

  eval_retrieval_title.py
  eval_generation_judge.py
  eval_latency_dataset.py
  run_faq_benchmark.py

  reports/
    faq_retrieval_metrics.json
    faq_generation_metrics.json
    faq_latency_metrics.json
    faq_per_sample_results.jsonl
    faq_latest_metrics.json
    faq_latest_report.md
```

Giữ lại file cũ nếu muốn, nhưng benchmark chính nên chuyển sang các file mới có chữ `faq` để tránh nhầm với benchmark template cũ.

---

## 4. Quy trình tổng thể

```text
Bước 1: Crawl FAQ detail pages
Bước 2: Parse question, answer, related procedure title
Bước 3: Clean text và lọc sample lỗi
Bước 4: Match expected procedure title với corpus hiện có
Bước 5: Xuất final testset chỉ gồm 3 field
Bước 6: Viết retrieval evaluator theo title
Bước 7: Viết generation evaluator theo reference answer
Bước 8: Viết latency evaluator chạy trên toàn bộ hoặc subset
Bước 9: Viết run_faq_benchmark.py gom toàn bộ metrics
Bước 10: Commit report + cập nhật README + sửa CV bullet
```

---

## 5. Bước 1 — Crawl FAQ data

### 5.1 Nguyên tắc crawl

Không crawl quá nhanh.

Config đề xuất:

```text
sleep_min = 0.7 giây
sleep_max = 2.0 giây
timeout = 20 giây
max_retries = 3
backoff = 2x
user_agent = "Mozilla/5.0 ... eGov-Bot academic benchmark crawler"
```

Không cần crawl toàn bộ 9452 câu ngay từ đầu. Làm theo từng mức:

```text
Full benchmark: 500 valid samples
```

### 5.2 Chiến lược crawl

Có 2 hướng.

#### Hướng A — Tìm API listing trong DevTools

Mở trang FAQ trong browser:

```text
https://dichvucong.gov.vn/p/home/dvc-cau-hoi-pho-bien.html
```

Mở DevTools → Network → XHR/Fetch → reload trang → tìm request trả về danh sách câu hỏi.

Nếu tìm được API listing:

1. Crawl list page để lấy `faq_id`.
2. Với mỗi `faq_id`, gọi detail URL.
3. Parse detail page.

Ưu điểm:

- Ít request lỗi.
- Không cần dò id.
- Có thể lấy đủ và đúng danh sách FAQ.

#### Hướng B — Dò id detail page

Nếu chưa tìm được API listing, dùng URL detail dạng:

```text
https://dichvucong.gov.vn/p/home/dvc-chi-tiet-cau-hoi.html?id={id}&row_limit=1
```

Dò id trong một khoảng hợp lý:

```bash
python evaluation/crawlers/crawl_dvc_faq_ids.py \
  --start-id 1 \
  --end-id 30000 \
  --max-valid 800 \
  --output evaluation/testsets/dvc_faq_raw.jsonl \
  --sleep-min 0.7 \
  --sleep-max 2.0
```

Lưu ý:

- ID có thể không liên tục.
- Có page không tồn tại hoặc thiếu dữ liệu.
- Chỉ lưu sample khi parse được đủ question, answer và related procedure title.

### 5.3 Output raw

File raw có thể chứa thêm field để debug:

```json
{
  "faq_id": 15180,
  "url": "https://dichvucong.gov.vn/p/home/dvc-chi-tiet-cau-hoi.html?id=15180&row_limit=1",
  "question": "Cá nhân đăng ký Bồi dưỡng nghiệp vụ đăng kiểm viên tàu cá phải nộp những loại giấy tờ gì?",
  "reference_answer": "Theo quy định tại Khoản 3, Điều 8 Thông tư số 23/2018/TT-BNNPTNT ...",
  "expected_procedure_title": "Cấp, cấp lại thẻ, dấu kỹ thuật đăng kiểm viên tàu cá",
  "crawl_status": "ok"
}
```

Raw file có `url` là được, nhưng final benchmark file sẽ bỏ `url`.

---

## 6. Bước 2 — Parse detail page

Tạo file:

```text
evaluation/crawlers/parse_dvc_faq_detail.py
```

### 6.1 Parse theo HTML selector nếu ổn định

Logic:

```text
question = text trong h1
answer = text sau nhãn "Trả lời:"
expected_procedure_title = link đầu tiên sau section "Các thủ tục liên quan"
```

### 6.2 Parse fallback bằng text lines

Vì site có thể render hơi khác, nên nên có fallback:

1. Dùng BeautifulSoup lấy toàn bộ text.
2. Chuẩn hóa thành list dòng không rỗng.
3. Tìm dòng bắt đầu bằng câu hỏi, thường là `h1` hoặc dòng sau `Tìm kiếm`.
4. Tìm index của dòng `Trả lời:`.
5. Lấy answer từ sau `Trả lời:` đến trước `Các thủ tục liên quan`.
6. Lấy title sau `Các thủ tục liên quan`, trước `Các câu hỏi liên quan`.

Pseudo-code:

```python
def parse_detail(html: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    question = parse_question(soup)
    lines = get_clean_lines(soup.get_text("\n"))

    answer = extract_between(
        lines,
        start_marker="Trả lời:",
        end_markers=["Các thủ tục liên quan", "Các câu hỏi liên quan"]
    )

    expected_title = extract_after_marker(
        lines,
        marker="Các thủ tục liên quan",
        stop_markers=["Các câu hỏi liên quan", "Thu nhỏ câu hỏi liên quan"]
    )

    if not question or not answer or not expected_title:
        return None

    return {
        "question": question,
        "reference_answer": answer,
        "expected_procedure_title": expected_title,
    }
```

### 6.3 Điều kiện sample hợp lệ

Chỉ giữ sample khi:

```text
question length >= 15 ký tự
reference_answer length >= 30 ký tự
expected_procedure_title length >= 10 ký tự
answer không chứa "Đang xử lý"
question không chứa "Đang xử lý"
expected_procedure_title không phải menu/header/footer
```

---

## 7. Bước 3 — Clean data

Tạo file:

```text
evaluation/utils/text_normalize.py
evaluation/clean_dvc_faq_testset.py
```

### 7.1 Text normalization

Hàm cần có:

```python
def normalize_text(s: str) -> str:
    s = html.unescape(s)
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s)
    s = s.strip()
    return s
```

### 7.2 Title normalization để match

```python
def normalize_title(s: str) -> str:
    s = normalize_text(s).lower()
    s = re.sub(r"[\.,;:!?'\"“”‘’()\[\]{}]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s
```

Không nên bỏ dấu tiếng Việt trong bước chính, vì bỏ dấu có thể gây match sai. Nếu cần fuzzy fallback thì mới dùng thêm bản không dấu.

### 7.3 Deduplicate

Loại trùng theo normalized question:

```text
key = normalize_title(question)
```

Nếu 2 sample cùng question:

- Giữ sample có answer dài hơn.
- Hoặc giữ sample parse được expected title tốt hơn.

### 7.4 Filter answer quá chung chung

Loại nếu answer thuộc dạng:

```text
Đang cập nhật
Không có thông tin
Vui lòng xem thủ tục liên quan
```

Loại nếu answer chỉ là 1 câu quá ngắn và không đủ ý.

---

## 8. Bước 4 — Match expected procedure title với corpus hiện có

Đây là bước rất quan trọng. Nếu `expected_procedure_title` không khớp với title trong corpus thì retrieval metric sẽ sai.

Corpus hiện tại thường nằm ở:

```text
static/data/toan_bo_du_lieu_final.json
```

Hoặc nếu dùng cache/HF:

```text
.cache/egov_data/toan_bo_du_lieu_final.json
```

### 8.1 Load title từ corpus

Tạo set title từ các field có thể có:

```python
candidate_title_fields = [
    "ten_thu_tuc",
    "title",
    "procedure_title",
    "name",
]
```

Ưu tiên `ten_thu_tuc` nếu corpus dùng tiếng Việt.

### 8.2 Exact normalized match

```python
corpus_title_map = {
    normalize_title(title): title
    for title in corpus_titles
}

key = normalize_title(expected_procedure_title)
if key in corpus_title_map:
    matched_title = corpus_title_map[key]
```

Nếu match exact, update title về đúng title trong corpus:

```json
"expected_procedure_title": matched_title
```

### 8.3 Fuzzy match cho trường hợp lệch nhẹ

Dùng RapidFuzz:

```bash
pip install rapidfuzz
```

Logic:

```python
from rapidfuzz import process, fuzz

best_title, score, _ = process.extractOne(
    normalize_title(expected_title),
    list(corpus_title_map.keys()),
    scorer=fuzz.token_set_ratio,
)

if score >= 92:
    matched_title = corpus_title_map[best_title]
else:
    send_to_manual_review
```

Không tự động nhận fuzzy dưới 92 để tránh match nhầm thủ tục gần giống nhau.

### 8.4 Manual review CSV

Các sample không match title thì ghi ra:

```text
evaluation/testsets/dvc_faq_manual_review.csv
```

Cột:

```text
question, reference_answer, expected_procedure_title, best_candidate_title, fuzzy_score
```

Sau đó review thủ công:

- Nếu đúng, sửa title.
- Nếu không chắc, loại sample.

### 8.5 Output clean full

File clean full có thể vẫn giữ debug field:

```text
evaluation/testsets/dvc_faq_clean_full.jsonl
```

Nhưng final eval file chỉ giữ 3 field.

---

## 9. Bước 5 — Xuất final testset chỉ gồm 3 field

Tạo script:

```text
evaluation/export_faq_eval_testset.py
```

Command:

```bash
python evaluation/export_faq_eval_testset.py \
  --input evaluation/testsets/dvc_faq_clean_full.jsonl \
  --output evaluation/testsets/dvc_faq_qa_500.jsonl \
  --limit 500 \
  --seed 42
```

Output mỗi dòng:

```json
{"question":"...","reference_answer":"...","expected_procedure_title":"..."}
```

Không thêm field khác trong final file.

### 9.1 Kiểm tra final file

Script check:

```bash
python evaluation/validate_faq_testset.py \
  --testset evaluation/testsets/dvc_faq_qa_500.jsonl
```

Validate:

```text
Không dòng rỗng
Mỗi dòng parse JSON được
Chỉ có đúng 3 keys: question, reference_answer, expected_procedure_title
Không duplicate question
Không missing field
question length >= 15
reference_answer length >= 30
expected_procedure_title length >= 10
```

---

## 10. Bước 6 — Viết retrieval evaluator theo title

Tạo file:

```text
evaluation/eval_retrieval_title.py
```

### 10.1 Input arguments

```bash
python evaluation/eval_retrieval_title.py \
  --testset evaluation/testsets/dvc_faq_qa_500.jsonl \
  --output evaluation/reports/faq_retrieval_metrics.json \
  --per-sample-output evaluation/reports/faq_retrieval_per_sample.jsonl \
  --k 10 \
  --mode hybrid
```

Arguments:

```text
--testset
--output
--per-sample-output
--k default 10
--mode bm25|dense|hybrid|hybrid_keyword
```

### 10.2 Lấy title từ result

Retriever result hiện có thể có các field như:

```text
result.title
result.metadata["ten_thu_tuc"]
result.metadata["title"]
```

Viết helper:

```python
def get_result_title(result) -> str:
    for attr in ["title", "procedure_title"]:
        if hasattr(result, attr) and getattr(result, attr):
            return getattr(result, attr)

    metadata = getattr(result, "metadata", {}) or {}
    for key in ["ten_thu_tuc", "title", "procedure_title", "name"]:
        if metadata.get(key):
            return metadata[key]

    return ""
```

### 10.3 Match logic

```python
def title_match(predicted_title: str, expected_title: str) -> bool:
    return normalize_title(predicted_title) == normalize_title(expected_title)
```

Có thể thêm fuzzy match chỉ để report, nhưng metric chính nên exact normalized match.

### 10.4 Metrics

Với mỗi sample:

```python
rank = vị trí đầu tiên trong top-k có title match, bắt đầu từ 1
```

Nếu không match:

```python
rank = None
```

Metrics:

```python
recall_at_1 = count(rank <= 1) / n
recall_at_3 = count(rank <= 3) / n
recall_at_5 = count(rank <= 5) / n
recall_at_10 = count(rank <= 10) / n
mrr_at_10 = mean(1 / rank if rank else 0)
ndcg_at_10 = mean(1 / log2(rank + 1) if rank else 0)
```

### 10.5 Per-sample output

```json
{
  "question": "...",
  "expected_procedure_title": "...",
  "rank": 2,
  "hit@1": false,
  "hit@3": true,
  "top_titles": ["...", "...", "..."],
  "latency_ms": 123
}
```

Per-sample output giúp debug vì biết câu nào fail và top title trả về là gì.

---

## 11. Bước 7 — Làm ablation BM25 vs Dense vs Hybrid

### 11.1 Mục tiêu

Không chỉ báo cáo Hybrid tốt/xấu, mà phải có baseline.

Cần chạy:

```bash
python evaluation/eval_retrieval_title.py --mode bm25
python evaluation/eval_retrieval_title.py --mode dense
python evaluation/eval_retrieval_title.py --mode hybrid
```

### 11.2 Nếu current HybridRetriever chưa hỗ trợ mode

Có 2 cách.

#### Cách A — Thêm parameter vào HybridRetriever

Thêm config:

```python
retriever.search(query, limit=k, mode="hybrid")
```

Mode:

```text
bm25: chỉ gọi BM25
 dense: chỉ gọi FAISS/vector
hybrid: gọi cả BM25 + FAISS rồi rank fusion
```

#### Cách B — Tạo evaluator gọi trực tiếp component

Nếu không muốn sửa core app, trong evaluator tạo wrapper:

```python
if mode == "bm25":
    results = retriever.search_bm25(query, limit=k)
elif mode == "dense":
    results = retriever.search_dense(query, limit=k)
else:
    results = retriever.search(query, limit=k)
```

Nếu current retriever chưa có public method `search_bm25` hoặc `search_dense`, có thể implement thêm private helper trong evaluator hoặc sửa retriever nhẹ.

### 11.3 Report ablation

Tạo file:

```text
evaluation/reports/faq_retrieval_ablation.md
```

Nội dung:

```markdown
# FAQ Retrieval Ablation

Testset: evaluation/testsets/dvc_faq_qa_500.jsonl
Count: 500
Date: yyyy-mm-dd
Environment: CPU/GPU/RAM, embedding model, data version

| Method | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR@10 | nDCG@10 | p95 latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 only | ... | ... | ... | ... | ... | ... | ... |
| Dense only | ... | ... | ... | ... | ... | ... | ... |
| Hybrid | ... | ... | ... | ... | ... | ... | ... |
```

---

## 12. Bước 8 — Generation evaluator với reference_answer

Tạo file:

```text
evaluation/eval_generation_judge.py
```

### 12.1 Command

```bash
python evaluation/eval_generation_judge.py \
  --base-url http://localhost:7860 \
  --testset evaluation/testsets/dvc_faq_qa_500.jsonl \
  --output evaluation/reports/faq_generation_metrics.json \
  --per-sample-output evaluation/reports/faq_generation_per_sample.jsonl \
  --limit 100 \
  --judge-provider gemini
```

Do chi phí API, có thể dùng `--limit 100` cho generation judge, còn retrieval thì chạy full 500.

### 12.2 Flow

Với mỗi sample:

1. Call `/chat`:

```json
{
  "question": "sample.question",
  "session_id": "eval-faq-{i}"
}
```

2. Lấy:

```text
model_answer
sources
top source titles
latency_ms
status_code
```

3. Check source title match:

```text
source_title_match = expected_procedure_title xuất hiện trong sources hay không
```

4. Judge answer so với reference answer.

### 12.3 LLM-as-judge prompt

Prompt nên yêu cầu output JSON nghiêm ngặt:

```text
Bạn là evaluator cho hệ thống hỏi đáp thủ tục hành chính tiếng Việt.

Nhiệm vụ: chấm câu trả lời của model dựa trên câu hỏi và câu trả lời tham chiếu chính thức.

Question:
{question}

Reference answer:
{reference_answer}

Model answer:
{model_answer}

Hãy đánh giá:
1. correctness_score: 1-5, câu trả lời có đúng và đủ ý so với reference không.
2. faithfulness_score: 1-5, câu trả lời có bám vào reference không, có thêm thông tin không có căn cứ không.
3. missing_information: danh sách ý quan trọng bị thiếu.
4. hallucinated_information: danh sách thông tin model bịa/thêm không có trong reference.
5. final_verdict: "pass" hoặc "fail".

Quy tắc:
- Không phạt nếu model diễn đạt khác nhưng cùng nghĩa.
- Phạt nặng nếu model thêm giấy tờ, lệ phí, thời hạn, cơ quan, điều kiện không có trong reference.
- PASS khi correctness_score >= 4, faithfulness_score >= 4 và không có hallucinated_information nghiêm trọng.

Chỉ trả về JSON hợp lệ, không markdown.
```

Expected judge output:

```json
{
  "correctness_score": 4,
  "faithfulness_score": 5,
  "missing_information": ["thiếu 02 ảnh màu 3x4 cm"],
  "hallucinated_information": [],
  "final_verdict": "pass"
}
```

### 12.4 Metrics tổng hợp

```python
metrics = {
    "count": n,
    "success_rate": success_count / n,
    "source_title_match_rate": source_match_count / n,
    "answer_correctness_avg": mean(correctness_scores),
    "faithfulness_avg": mean(faithfulness_scores),
    "pass_rate": pass_count / n,
    "hallucination_rate": hallucination_count / n,
    "latency_p50_ms": p50(latencies),
    "latency_p95_ms": p95(latencies),
}
```


## 13. Bước 9 — Latency benchmark trên FAQ testset

Tạo file:

```text
evaluation/eval_latency_dataset.py
```

### 13.1 Command

```bash
python evaluation/eval_latency_dataset.py \
  --base-url http://localhost:7860 \
  --testset evaluation/testsets/dvc_faq_qa_500.jsonl \
  --output evaluation/reports/faq_latency_metrics.json \
  --limit 100
```

### 13.2 Metrics

```text
count
success_rate
latency_min_ms
latency_mean_ms
latency_p50_ms
latency_p90_ms
latency_p95_ms
latency_p99_ms
latency_max_ms
```

Nếu API response có breakdown thì lưu thêm:

```text
retrieval_latency_ms
generation_latency_ms
total_latency_ms
```

Nếu hiện chưa có breakdown, giữ total latency trước. Sau này nâng cấp API sau.

### 13.3 Cold vs warm

Chạy 2 lần:

```text
Cold run: ngay sau khi start server
Warm run: sau khi server đã load model/index và chạy thử vài câu
```

Report nên ghi rõ là warm hay cold.

---

## 14. Bước 10 — Runner tổng hợp

Tạo file:

```text
evaluation/run_faq_benchmark.py
```

Command:

```bash
python evaluation/run_faq_benchmark.py \
  --testset evaluation/testsets/dvc_faq_qa_500.jsonl \
  --base-url http://localhost:7860 \
  --generation-limit 100
```

Runner làm:

```text
1. Validate testset
2. Run retrieval bm25
3. Run retrieval dense
4. Run retrieval hybrid
5. Check API /health
6. Run generation judge nếu API available
7. Run latency nếu API available
8. Write latest_metrics.json
9. Write latest_report.md
```

Nếu API chưa chạy:

```text
- Vẫn chạy retrieval benchmark.
- Generation/latency marked as skipped.
- Report ghi rõ lý do skipped.
```

---

## 15. Bước 11 — Report format

Tạo file:

```text
evaluation/reports/faq_latest_report.md
```

Nội dung mẫu:

```markdown
# eGov-Bot FAQ Benchmark Report

## 1. Testset

- Source: official FAQ-style questions from Vietnamese National Public Service Portal.
- Final schema: question, reference_answer, expected_procedure_title.
- Testset size: 500.
- Corpus: procedure-only corpus from current eGov-Bot data.
- Note: FAQ answers are used as reference answers, not as retrieval corpus, unless explicitly stated.

## 2. Retrieval Results

| Method | Recall@1 | Recall@3 | Recall@5 | Recall@10 | MRR@10 | nDCG@10 | p95 latency |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 only | ... | ... | ... | ... | ... | ... | ... |
| Dense only | ... | ... | ... | ... | ... | ... | ... |
| Hybrid | ... | ... | ... | ... | ... | ... | ... |

## 3. Generation Results

| Metric | Value |
|---|---:|
| Success rate | ... |
| Source title match | ... |
| Correctness avg | ... / 5 |
| Faithfulness avg | ... / 5 |
| Pass rate | ... |
| Hallucination rate | ... |
| p50 latency | ... ms |
| p95 latency | ... ms |

## 4. Failure Analysis

### Common retrieval failures

- Query too vague.
- Related procedure title in FAQ differs from corpus title.
- Multiple procedures have similar names.

### Common generation failures

- Missing one required document.
- Answer too generic.
- Added unsupported details.

## 5. Next Improvements

- Add reranker.
- Add query rewriting for vague FAQ questions.
- Add better citation/title matching.
- Add human spot-check set.
```

---

## 16. Bước 12 — Cập nhật README

Trong README, thêm section:

```markdown
## Evaluation

We evaluate eGov-Bot on official FAQ-style questions collected from the Vietnamese National Public Service Portal. Each final test sample contains:

```json
{"question":"...","reference_answer":"...","expected_procedure_title":"..."}
```

### Retrieval benchmark

Measures whether the retriever returns the expected administrative procedure title in top-k results.

Metrics: Recall@1, Recall@3, Recall@5, MRR@10, nDCG@10.

### Generation benchmark

Measures whether the generated answer matches the official reference answer and avoids unsupported information.

Metrics: correctness, faithfulness, hallucination rate, pass rate, and latency.
```

Sau khi có số thật thì thêm bảng kết quả. Không ghi số nếu chưa chạy thật.

---

## 17. Bước 13 — Cập nhật CV bullet sau khi chạy benchmark

Chỉ dùng câu có số liệu khi đã có report thật.

### Trước khi có số

```latex
\item Built a Dockerized Vietnamese e-government RAG chatbot with hybrid BM25 + FAISS retrieval, source-grounded Gemini generation, multi-turn context handling, SQLite feedback logging, and an FAQ-based evaluation pipeline.
```

### Sau khi có số thật

```latex
\item Built a Dockerized Vietnamese e-government RAG chatbot with hybrid BM25 + FAISS retrieval, source-grounded Gemini generation, and SQLite feedback logging.
\item Constructed an official FAQ-based benchmark with 500 question-answer-procedure samples from the National Public Service Portal, evaluating retrieval via Recall@k/MRR/nDCG and answer quality via correctness, faithfulness, hallucination rate, and latency.
\item Benchmarked BM25, dense retrieval, and hybrid retrieval, with hybrid retrieval achieving X Recall@5, Y MRR@10, and Z p95 end-to-end latency.
```

Thay X/Y/Z bằng số thật từ report.

---

## 18. Checklist implementation chi tiết

### Phase 1 — Data crawl

- [ ] Tạo branch mới: `benchmark/faq-evaluation`.
- [ ] Tạo folder `evaluation/crawlers`.
- [ ] Viết `parse_dvc_faq_detail.py`.
- [ ] Test parse với id `15180`.
- [ ] Viết `crawl_dvc_faq_ids.py`.
- [ ] Crawl thử 20 valid samples.
- [ ] Kiểm tra raw output bằng mắt.
- [ ] Crawl valid samples.

### Phase 2 — Data cleaning

- [ ] Viết `text_normalize.py`.
- [ ] Viết `title_matching.py`.
- [ ] Viết `clean_dvc_faq_testset.py`.
- [ ] Load corpus title từ `toan_bo_du_lieu_final.json`.
- [ ] Exact normalized title matching.
- [ ] Fuzzy matching với threshold >= 92.
- [ ] Xuất manual review CSV cho sample không match.
- [ ] Loại duplicate question.
- [ ] Loại answer/title/question lỗi.
- [ ] Xuất `dvc_faq_clean_full.jsonl`.

### Phase 3 — Final testset

- [ ] Viết `export_faq_eval_testset.py`.
- [ ] Xuất `dvc_faq_qa_300.jsonl`.
- [ ] Xuất `dvc_faq_qa_500.jsonl` nếu đủ data.
- [ ] Viết `validate_faq_testset.py`.
- [ ] Đảm bảo final testset chỉ có 3 keys.

### Phase 4 — Retrieval evaluation

- [ ] Viết `eval_retrieval_title.py`.
- [ ] Implement `get_result_title()`.
- [ ] Implement `normalize_title()`.
- [ ] Implement Recall@1/3/5/10.
- [ ] Implement MRR@10.
- [ ] Implement nDCG@10.
- [ ] Save per-sample failures.
- [ ] Chạy hybrid mode.
- [ ] Chạy BM25-only mode.
- [ ] Chạy dense-only mode.
- [ ] Tạo ablation table.

### Phase 5 — Generation evaluation

- [ ] Viết `eval_generation_judge.py`.
- [ ] Call `/chat` theo từng sample.
- [ ] Extract answer/sources/latency.
- [ ] Check source title match.
- [ ] Viết judge prompt.
- [ ] Parse judge JSON robustly.
- [ ] Retry judge nếu output không phải JSON.
- [ ] Save per-sample result.
- [ ] Tổng hợp correctness/faithfulness/pass/hallucination.
- [ ] Human spot-check 30-50 mẫu nếu có thời gian.

### Phase 6 — Latency evaluation

- [ ] Viết `eval_latency_dataset.py`.
- [ ] Chạy 100 FAQ questions.
- [ ] Report p50/p90/p95/p99.
- [ ] Ghi rõ cold/warm.

### Phase 7 — Report and README

- [ ] Viết `run_faq_benchmark.py`.
- [ ] Generate `faq_latest_metrics.json`.
- [ ] Generate `faq_latest_report.md`.
- [ ] Update README Evaluation section.
- [ ] Commit report sample hoặc latest report.
- [ ] Không ghi số benchmark lên README nếu chưa chạy thật.

---

## 19. Commands gợi ý từ đầu đến cuối

### 19.1 Setup

```bash
git checkout -b benchmark/faq-evaluation
pip install beautifulsoup4 requests rapidfuzz pandas tqdm
```

### 19.2 Test parser một page

```bash
python evaluation/crawlers/parse_dvc_faq_detail.py \
  --url "https://dichvucong.gov.vn/p/home/dvc-chi-tiet-cau-hoi.html?id=15180&row_limit=1"
```

Expected output:

```json
{
  "question": "Cá nhân đăng ký Bồi dưỡng nghiệp vụ đăng kiểm viên tàu cá phải nộp những loại giấy tờ gì?",
  "reference_answer": "Theo quy định tại Khoản 3, Điều 8 Thông tư số 23/2018/TT-BNNPTNT ...",
  "expected_procedure_title": "Cấp, cấp lại thẻ, dấu kỹ thuật đăng kiểm viên tàu cá"
}
```

### 19.3 Crawl raw

```bash
python evaluation/crawlers/crawl_dvc_faq_ids.py \
  --start-id 1 \
  --end-id 30000 \
  --max-valid 800 \
  --output evaluation/testsets/dvc_faq_raw.jsonl \
  --sleep-min 0.7 \
  --sleep-max 2.0
```

### 19.4 Clean and match title

```bash
python evaluation/clean_dvc_faq_testset.py \
  --input evaluation/testsets/dvc_faq_raw.jsonl \
  --corpus static/data/toan_bo_du_lieu_final.json \
  --output evaluation/testsets/dvc_faq_clean_full.jsonl \
  --manual-review-output evaluation/testsets/dvc_faq_manual_review.csv
```

### 19.5 Export final 3-field testset

```bash
python evaluation/export_faq_eval_testset.py \
  --input evaluation/testsets/dvc_faq_clean_full.jsonl \
  --output evaluation/testsets/dvc_faq_qa_500.jsonl \
  --limit 500 \
  --seed 42
```

### 19.6 Validate final testset

```bash
python evaluation/validate_faq_testset.py \
  --testset evaluation/testsets/dvc_faq_qa_500.jsonl
```

### 19.7 Run retrieval benchmark

```bash
python evaluation/eval_retrieval_title.py \
  --testset evaluation/testsets/dvc_faq_qa_500.jsonl \
  --mode bm25 \
  --output evaluation/reports/faq_retrieval_bm25.json

python evaluation/eval_retrieval_title.py \
  --testset evaluation/testsets/dvc_faq_qa_500.jsonl \
  --mode dense \
  --output evaluation/reports/faq_retrieval_dense.json

python evaluation/eval_retrieval_title.py \
  --testset evaluation/testsets/dvc_faq_qa_500.jsonl \
  --mode hybrid \
  --output evaluation/reports/faq_retrieval_hybrid.json
```

### 19.8 Start app

```bash
python scripts/run_dev.py
```

Hoặc Docker:

```bash
docker compose up --build
```

### 19.9 Run generation judge

```bash
python evaluation/eval_generation_judge.py \
  --base-url http://localhost:7860 \
  --testset evaluation/testsets/dvc_faq_qa_500.jsonl \
  --limit 100 \
  --output evaluation/reports/faq_generation_metrics.json \
  --per-sample-output evaluation/reports/faq_generation_per_sample.jsonl
```

### 19.10 Run all

```bash
python evaluation/run_faq_benchmark.py \
  --testset evaluation/testsets/dvc_faq_qa_500.jsonl \
  --base-url http://localhost:7860 \
  --generation-limit 100
```

---

## 20. Definition of Done

Project benchmark được coi là đạt khi có đủ:

```text
1. Có final testset 300-500 samples, mỗi sample chỉ gồm question, reference_answer, expected_procedure_title.
2. 100% sample final không thiếu field.
3. 95%+ sample final có expected_procedure_title match được với title trong corpus.
4. Có retrieval benchmark cho BM25-only, dense-only, hybrid.
5. Có metrics Recall@1/3/5/10, MRR@10, nDCG@10.
6. Có generation benchmark ít nhất 100 samples.
7. Có metrics correctness, faithfulness, hallucination rate, pass rate, latency p50/p95.
8. Có per-sample failure file để debug.
9. Có latest_report.md trình bày rõ testset, method, result, failure analysis.
10. README có section Evaluation và không ghi claim quá đà.
```

---

## 21. Những lỗi cần tránh

### 21.1 Không đưa FAQ answer vào retrieval corpus khi benchmark chính

Nếu cho bot index cả FAQ answer, benchmark sẽ dễ hơn nhiều vì answer có sẵn trong corpus.

Benchmark chính nên là:

```text
Question từ FAQ
Reference answer từ FAQ
Corpus retrieval là procedure data hiện tại
Expected match là procedure title
```

Nếu muốn thêm benchmark FAQ-indexed thì ghi rõ là benchmark phụ.

### 21.2 Không ghi số lên CV nếu chưa chạy thật

Không ghi:

```text
Achieved high accuracy
Improved performance significantly
Reduced hallucination
```

Khi chưa có số cụ thể.

### 21.3 Không dùng fuzzy match quá dễ trong metric chính

Fuzzy match có thể làm metric đẹp ảo.

Metric chính nên dùng exact normalized title match.

Fuzzy chỉ dùng cho cleaning/manual review.

### 21.4 Không chỉ đo generation bằng độ dài answer

Answer dài không có nghĩa là đúng.

Phải đo ít nhất:

```text
correctness
faithfulness
hallucination
```

### 21.5 Không crawl quá nhanh

Crawl chậm, có retry, có checkpoint. Nếu bị lỗi nhiều thì dừng và giảm tốc độ.

---

## 22. Ưu tiên nếu thời gian ít

Nếu chỉ có 1-2 ngày, làm minimal version này:

```text
1. Crawl 300 FAQ samples.
2. Clean ra final 3-field testset.
3. Eval retrieval title match với Hybrid only.
4. Eval generation 50-100 samples bằng LLM-as-judge.
5. Viết latest_report.md.
```

Nếu có thêm thời gian:

```text
6. Thêm BM25-only vs Dense-only vs Hybrid ablation.
7. Thêm human spot-check.
8. Thêm failure analysis.
9. Thêm README benchmark section.
```

---

## 23. Kết quả mong muốn sau khi hoàn thành

Sau khi làm xong, project có thể mô tả chuyên nghiệp hơn:

```text
eGov-Bot is a Vietnamese e-government RAG chatbot evaluated on an official FAQ-derived benchmark. The benchmark uses real user-style questions, official reference answers, and expected administrative procedure titles. The evaluation measures retrieval quality with Recall@k/MRR/nDCG, answer quality with correctness/faithfulness/hallucination checks, and system performance with p50/p95 latency.
```

CV bullet sau khi có số thật sẽ mạnh hơn nhiều vì có:

- Data test thực tế từ nguồn official.
- Evaluation methodology rõ ràng.
- Retrieval metrics.
- Generation quality metrics.
- Latency metrics.
- Baseline/ablation.

