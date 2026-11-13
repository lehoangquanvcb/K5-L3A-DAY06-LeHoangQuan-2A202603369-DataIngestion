# Báo cáo cá nhân Day 06 — BCTC hợp nhất VIC 2025

**Học viên** Lê Hoàng Quân · **MSSV** 2A202603369 · **Lớp** K5-L3A

## Dữ liệu và pipeline

Nguồn là BCTC hợp nhất kiểm toán năm 2025 do Vingroup công bố. PDF có 126 trang vật lý. Render trang 17–56 ở 300 DPI bằng PyMuPDF, sau đó OCR tiếng Việt bằng Tesseract. Giữ 37 trang có nội dung sử dụng được, tổng cộng 90.287 ký tự sau chuẩn hóa. Loại trang 52, 53, 56 vì OCR sai hướng. Dùng Unicode NFC và giữ ranh giới đoạn. [Manifest và nguồn tải](../../data/manifest.json)

FastEmbed 0.9.1 chạy `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` qua ONNX trên CPU, tạo vector 384 chiều. Qdrant local 1.20.0 lưu bền vững và tìm cosine chính xác. Chi phí dịch vụ 0 USD. Nạp lại cùng corpus giữ nguyên số chunk. Metadata gồm ID tài liệu, nguồn, trang PDF, trang in, section và note_topic. note_topic dựa trên tiêu đề nhóm thuyết minh. Trang 21 giao giữa hai nhóm nên nhãn theo trang có giới hạn. [Lệnh tái lập](../../README.md)

## Cấu hình và benchmark

A dùng cửa sổ 500 ký tự và overlap 50. B gom theo đoạn, giới hạn 500 ký tự và overlap 80 khi phải chia đoạn dài. C dùng chung index B, chỉ thêm filter note_topic khi câu hỏi xác định phạm vi. Cả ba dùng cùng corpus và model.

Bộ câu hỏi gồm 15 dev và 5 test, tách theo trang trước khi chạy. Có 4 câu có filter, gồm 1 câu test. Đáp án và đoạn bằng chứng được đối chiếu ảnh PDF gốc. Chọn theo Evidence Hit@3 trên dev, sau đó Hit@1 và chi phí ingest. Hit tự động yêu cầu đúng nguồn, đúng trang và đủ bằng chứng OCR chuẩn hóa trong một chunk. [Bộ benchmark](../../benchmark/vic_fy2025.json)

## Kết quả

| Cấu hình | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 | Chunk | Ingest lần đầu |
|---|---:|---:|---:|---:|---:|---:|
| A | 2/15 | 3/15 | 2/5 | 2/5 | 212 | 9,32 s |
| B | 7/15 | 7/15 | 2/5 | 2/5 | 273 | 11,60 s |
| C | 8/15 | 8/15 | 2/5 | 2/5 | 273 | Chung B |

Thời gian ingest đo trong môi trường chạy của Codex. Lần chạy của học viên trên Windows tái lập các chỉ số retrieval.

| Cấu hình | Coherence /2 (10 vị trí) | Metadata khớp OCR và manifest | Filter dev | Filter test | Grounding 0/1/2 (5 câu) | Grounding /2 |
|---|---:|---:|---:|---:|---|---:|
| A | 1,1 | 15/15 | 1/3 | 0/1 | 2 / 1 / 2 | 1,0 |
| B | 1,8 | 15/15 | 1/3 | 0/1 | 3 / 0 / 2 | 0,8 |
| C | 1,8 | 15/15 | 3/3 | 1/1 | 3 / 0 / 2 | 0,8 |

Coherence được chấm trên chunk đầu tiên chứa mốc giữa trang cho 10 trang PDF 17–26. Grounding được chấm trên top-3 của 5 câu test. Metadata được đối chiếu với snapshot OCR và manifest. Trace đầy đủ được sinh cục bộ tại `.day06-vic/dev.json` và `.day06-vic/test.json`. [Chỉ số gốc](../../results/vic_retrieval_summary.json) · [Nhãn và lý do audit](../../results/vic_trace_audit.md)

## Phân tích và kết luận

A–B tăng Evidence Hit@3 trên dev từ 3/15 lên 7/15 và tăng coherence từ 1,1 lên 1,8. B có thêm 61 chunk và mất khoảng 2,28 giây ingest lần đầu. B–C tăng từ 7/15 lên 8/15 trên dev. C được chọn theo tiêu chí đã chốt. Cả ba đạt 2/5 trên test nên tập này chưa cho thấy lợi thế retrieval của C.

- **q16, PDF 33:** C lọc đúng nhóm chính sách kế toán nhưng trả các trang 26, 23 và 32, bỏ lỡ điều kiện hoàn nhập dự phòng bảo hành vào thu nhập khác.
- **q17, PDF 38:** A trả đúng trang nhưng chunk cắt trước điều kiện hoàn thành nghĩa vụ. B/C trả PDF 42, 46 và 54.
- **q19, PDF 49:** các kết quả về phải thu và cho vay thiếu đoạn phân loại nợ xấu.

Giới hạn gồm một báo cáo, 5 câu test, lỗi OCR và metadata theo trang. Một thí nghiệm tiếp theo có thể giữ tiêu đề tiểu mục trong chunk và đánh giá trên bộ test mới.

## Sử dụng AI

ChatGPT/Codex hỗ trợ rà OCR, soạn benchmark, đối chiếu PDF, viết pipeline và gán nhãn audit từ trace thật. Học viên cung cấp dữ liệu OCR và tái lập dev/test trên Windows.
