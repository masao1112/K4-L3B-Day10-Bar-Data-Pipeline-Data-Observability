# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Thành Tiến |
| MSSV | 2A202603003 |
| Khóa/Lớp | K4 |
| Tên nhóm | Bar |
| Vai trò chính | Data Acquisition & Benchmarking |
| Repository | https://github.com/masao1112/K4-L3B-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Thu thập dữ liệu từ Crossref | `src/ingestion/crossref.py` | API Crossref, query và bộ lọc kết quả | Raw records `data/raw/crossref_records.json` và response snapshot `data/raw/crossref_response.json` | Hoàn thành |
| Thiết kế benchmark đánh giá | `src/evaluation/testset.py` | Clean dataset + metadata bài báo | `data/eval/test_set.json` với 10 câu hỏi, ground truth document IDs | Hoàn thành |

Chỉ nhận ownership cho phần tôi trực tiếp thực hiện. Tôi phụ trách phần thu thập dữ liệu và thiết lập tập benchmark để đánh giá chất lượng retrieval và câu trả lời của hệ thống RAG.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Hỗ trợ kiểm tra schema và data contract | `src/ingestion/cleaning.py` | Đảm bảo metadata từ Crossref được giữ đúng và tương thích với schema sạch của pipeline |
| Hỗ trợ đối chiếu output benchmark | `src/pipelines/phase1.py` | Giữ tập test cố định để so sánh hiệu suất baseline, corrupted và repaired |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Lấy dữ liệu raw từ Crossref | `src/ingestion/crossref.py`, `data/raw/crossref_records.json` | Thu thập thành công 24 bài báo với metadata đầy đủ | Kiểm tra file raw JSON và đối chiếu số lượng record |
| Tạo bộ test set cho đánh giá | `src/evaluation/testset.py`, `data/eval/test_set.json` | Tạo 10 câu hỏi benchmark với 4 nhóm kiểu câu hỏi: summary, authors, date, categories | Duyệt tập câu hỏi và đối chiếu ground truth document IDs |
| Đảm bảo benchmark đồng nhất giữa các pha | `data/eval/test_set.json` | Baseline, corrupted và repaired được đánh giá trên cùng tập test | Chạy pipeline và so sánh các file metrics tương ứng |

Nêu một output cụ thể mà phần việc của tôi tạo ra hoặc giúp xác minh:

Tập benchmark `data/eval/test_set.json` cùng với snapshot raw dữ liệu `data/raw/crossref_records.json` là hai artifact quan trọng nhất. Chúng tạo nền tảng để đánh giá liệu hồi phục chất lượng dữ liệu có làm cải thiện hiệu suất retrieval và answer quality hay không.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong một pipeline RAG, chất lượng dữ liệu đầu vào và bộ đánh giá là yếu tố quyết định đến độ tin cậy của kết quả cuối cùng. Nếu không có nguồn dữ liệu chuẩn và bộ benchmark ổn định, hệ thống có thể cho ra điểm số đẹp nhưng không phản ánh đúng chất lượng thực tế. Vì vậy, phần việc của tôi tập trung vào việc thu thập dữ liệu từ Crossref một cách đáng tin cậy và tạo tập test cố định để đánh giá đúng các pha pipeline.

### Cách triển khai

Tôi thực hiện việc trích xuất dữ liệu từ Crossref REST API theo các query và bộ lọc rõ ràng, sau đó lưu raw snapshot dưới dạng JSON để làm nguồn dữ liệu gốc. Sau đó, tôi chuẩn hóa benchmark theo nhóm câu hỏi đã định nghĩa: summary, authors, date và categories. Mỗi câu hỏi đi kèm ground-truth document ID, giúp hệ thống đánh giá retrieval hit rate, token F1 và judge score trên cùng một tiêu chuẩn xuyên suốt.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref API response, metadata bài báo, tiêu chí benchmark |
| Output | `data/raw/crossref_records.json`, `data/eval/test_set.json` |
| Module phụ thuộc | `src/ingestion/cleaning.py`, `src/pipelines/phase1.py`, `src/observability/quality.py` |
| Module sử dụng output | `src/pipelines/phase1.py`, `src/evaluation/metrics.py`, `src/retrieval/qa.py` |
| Điều kiện lỗi cần xử lý | API rate limit, thiếu abstract, thiếu DOI, schema không đồng nhất, metadata không chứa `published` |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Dữ liệu raw được thu thập, benchmark được lưu trong `data/eval/test_set.json`, và kết quả metrics của baseline/corrupted/repaired có thể so sánh trực tiếp.
- **Kết quả thực tế:** Pipeline chạy thành công với dữ liệu benchmark ổn định; baseline đạt 1.0000 ở retrieval hit rate và F1, trong khi corrupted giảm rõ rệt và repaired phục hồi hoàn toàn.
- **Artifact/log:** `data/raw/crossref_records.json`, `data/eval/test_set.json`, `data/results/*_metrics.json`, `data/reports/*.md`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Trong các bài lab về data observability, chỉ số đánh giá dễ bị sai lệch nếu dùng tập câu hỏi khác nhau qua từng pha pipeline.
- **Các phương án đã cân nhắc:**
  1. Tạo test set mới mỗi lần chạy pipeline.
  2. Duy trì cùng một benchmark cố định xuyên suốt baseline, corrupted và repaired.
- **Phương án đã chọn:** Duy trì cùng one test set cố định.
- **Lý do:** Điều này giúp biến đổi hiệu năng thật sự phản ánh chất lượng dữ liệu và vector store, không bị nhiễu bởi sự thay đổi độ khó câu hỏi.
- **Bằng chứng quyết định phù hợp:** Baseline và repaired cùng đạt `retrieval_hit_rate = 1.0000`, còn corrupted giảm xuống `0.6000`, cho thấy benchmark cố định là hợp lý và đáng tin cậy.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Dữ liệu thu thập hoặc benchmark không đồng nhất giữa các pha, dẫn đến khó so sánh chính xác kết quả.
- **Lệnh hoặc bước tái hiện:** Chạy các pipeline theo từng pha mà không giữ cùng tập test, hoặc gặp trường hợp `summary` bị thiếu, DOI bị rỗng, hoặc metadata `published` không hợp lệ.
- **Nguyên nhân gốc:** Không có schema chuẩn và không có benchmark cố định; ngoài ra Crossref API có thể trả về metadata thiếu trường cần thiết.
- **Cách xử lý:** Giữ raw snapshot, validate DOI và required fields, tạo benchmark cố định cùng ground-truth document IDs; sau đó dùng chung bộ test cho tất cả pha.
- **Cách xác minh sau khi sửa:** Chạy lại pipeline và kiểm tra `data/eval/test_set.json` cùng các file metrics ở `data/results`.
- **Điều học được:** Dữ liệu đầu vào tốt không chỉ là nguồn dữ liệu đủ số lượng, mà là dữ liệu đúng schema, đúng ground truth và được đánh giá trên cùng tập chuẩn.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
   - Crossref API trả về raw papers metadata, sau đó dữ liệu được lưu vào `data/raw/crossref_records.json`. Tiếp theo, dữ liệu sạch được tạo trong `data/clean`, rồi được embedding và index vào ChromaDB.
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
   - Mỗi câu hỏi benchmark có một paper_id tương ứng. Retrieval thành công nếu top-k trả về đúng ground-truth paper; câu trả lời được so khớp với gold answer để tính F1 và judge score.
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
   - Quality checks kiểm tra tính đầy đủ, unique, dài field và schema; freshness monitoring đo độ mới của dữ liệu theo ngưỡng 180 ngày.
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
   - Để đảm bảo mọi thay đổi trong metric đều xuất phát từ dữ liệu và index chứ không phải do câu hỏi thay đổi.
5. Repair được xem là thành công dựa trên artifact và metric nào?
   - Nếu dữ liệu được rebuild từ raw snapshot, quality gate PASS và các metric phục hồi về mức baseline, đặc biệt `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | Tỷ lệ truy hồi phục hồi hoàn toàn sau repair |
| `mean_token_f1` | 1.0000 | 0.5817 | 1.0000 | Chất lượng trả lời hồi phục 100% |
| `judge_accuracy` | 1.0000 | 0.6000 | 1.0000 | Đánh giá người giám sát cũng trả lại hiệu quả như ban đầu |
| `mean_judge_score` | 5.00 | 3.20 | 5.00 | Điểm trung bình phục hồi hoàn toàn |
| Quality checks | PASS | FAIL | PASS | Dữ liệu sạch sau repair đạt chuẩn |
| Freshness status | PASS | FAIL / stale | PASS | Chất lượng data được khôi phục |

### Kết luận từ số liệu

1. Data corruption → quality/freshness signal thay đổi → agent metric thay đổi.
   - Khi dữ liệu bị nhiễu và vi phạm unique/length, quality gate FAIL; đồng thời hệ thống RAG mất hiệu suất rõ rệt.
2. Repair action → quality/freshness signal phục hồi → agent metric phục hồi.
   - Khi data được rebuild từ raw snapshot, quality gate PASS và metrics trung bình trở lại mức baseline.

Corruption nào ảnh hưởng rõ nhất và vì sao?

Loại lỗi khiến dữ liệu mất tính nhất quán và làm mất khả năng định danh như `paper_id` trùng lặp, summary quá ngắn hoặc rỗng là ảnh hưởng rõ nhất vì nó trực tiếp làm sai lệch retrieval và không còn đủ ngữ nghĩa để trả lời chính xác.

Kết quả nào khác với kỳ vọng ban đầu?

Kết quả này cho thấy data quality không chỉ là vấn đề hiển thị; nó ảnh hưởng trực tiếp đến hiệu suất retrieval và chất lượng câu trả lời, đặc biệt trong mô hình RAG. Việc khôi phục dữ liệu từ snapshot gốc mang lại tác động đáng kể và phản hồi rất rõ trên các metric.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw data source phải được lưu lại để phục hồi dữ liệu khi pipeline bị lỗi hoặc nhiễu.
2. Benchmark phải cố định để so sánh đúng giữa các pha và tránh đánh giá sai lệch.
3. Data observability không chỉ là báo cáo, mà còn là cơ chế cảnh báo sớm trước khi hệ thống agent bị silent failure.

### Nếu có thêm thời gian

Tôi muốn cải thiện thêm tính năng linh hoạt của bộ benchmark bằng cách thêm các câu hỏi khó hơn và xác định rõ hơn mức độ ảnh hưởng của từng loại corruption lên từng nhóm câu hỏi (summary, authors, date, categories).

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thành Tiến
**Ngày xác nhận:** 2026-09-26
