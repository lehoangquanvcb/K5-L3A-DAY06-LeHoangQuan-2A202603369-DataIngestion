# Day 06 · Data Ingestion Engineering

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Chạy bài VIC FY2025 trên Windows

Mở PowerShell ở thư mục gốc repo. Dùng Python 3.11. Qdrant chạy cục bộ và lưu bền vững. FastEmbed tải bản ONNX của `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` từ Hugging Face lần đầu (khoảng 220 MB), sau đó tạo embedding 384 chiều trên CPU. Query và tài liệu dùng cùng model, không thêm tiền tố. Chi phí dịch vụ bằng 0.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\starter\requirements-vic.txt
$ocr = Join-Path $env:USERPROFILE "Day06-VIC-OCR"
.\.venv\Scripts\python.exe -m starter.src.run --ocr-dir "$ocr" --split dev
.\.venv\Scripts\python.exe -m starter.src.run --ocr-dir "$ocr" --split test
```

`$ocr` phải trỏ đến thư mục chứa trực tiếp `page-017.txt` đến `page-056.txt`. Nếu cần tái tạo, lấy PDF theo [manifest](data/manifest.json), render các trang vật lý 17–56 ở 300 DPI bằng PyMuPDF rồi OCR từng ảnh bằng Tesseract tiếng Việt (`-l vie`), xuất UTF-8. Các trang 52, 53, 56 bị loại do OCR sai hướng. Khi tái OCR bằng bản Tesseract hoặc dữ liệu tiếng Việt khác, số ký tự có thể thay đổi; cần rà lại các trang và gold evidence trước khi dùng snapshot mới.

- A dùng cửa sổ 500 ký tự, overlap 50. B gom đoạn trong giới hạn 500 ký tự; đoạn dài hơn dùng cửa sổ có overlap 80. C dùng đúng collection của B và áp dụng `note_topic` khi benchmark có filter. Qdrant local tìm cosine chính xác.
- Chọn theo Evidence Hit@3 trên dev, sau đó Hit@1 và chi phí dịch vụ ingest. Nếu mọi tiêu chí bằng nhau, chọn theo thứ tự A, B, C. Lệnh test dùng kết quả dev đã ghi và kiểm tra dấu vân tay của đầu vào. Hit tự động yêu cầu đúng trang và có đủ chuỗi evidence chuẩn hóa trong một chunk.
- `.day06-vic/dev.json` và `.day06-vic/test.json` chứa metrics, thời gian và trace top-3. `.day06-vic/coherence_samples.json` chứa 10 vị trí nguồn để chấm thủ công. Dùng trace test để đối chiếu metadata và chấm grounding 0–2. Kiểm tra quyền chia sẻ trước khi đưa trace chứa văn bản OCR lên GitHub.
- Chạy lại với cùng đầu vào để kiểm tra `reused` và số chunk. Dữ liệu đổi tạo collection mới theo dấu vân tay; dùng `--work-dir` riêng cho mỗi lần thí nghiệm nếu cần giữ kết quả trước đó.

## Tài liệu khởi đầu của lab

Dùng [starter PostgreSQL + pgvector](starter/README.md) để dựng database và hoàn thiện các hàm TODO, hoặc tự chọn vector store tương đương. Starter chỉ là khung: **bạn tự hiện thực pipeline và benchmark**.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/MSSV_HoTen.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) chỉ minh họa định dạng, không phải corpus đủ điều kiện. Phần xử lý và benchmark do bạn tự hiện thực; không bắt buộc xây chatbot.
