# Kết quả và audit Day 06 — VIC FY2025

Corpus gồm 37 trang OCR từ BCTC hợp nhất VIC 2025. So sánh chia cố định (A), chia theo đoạn (B) và chia theo đoạn với bộ lọc note_topic (C), dùng MiniLM đa ngữ 384 chiều và Qdrant local. Chi phí dịch vụ 0 USD. C dùng chung index B. Lần chạy Windows tái lập các điểm retrieval từ lần chạy Codex.

| Cấu hình | Dev Hit@1 | Dev Evidence Hit@3 | Test Hit@1 | Test Evidence Hit@3 | Chunk | Ingest lần đầu |
|---|---:|---:|---:|---:|---:|---:|
| A | 2/15 | 3/15 | 2/5 | 2/5 | 212 | 9,32 s |
| B | 7/15 | 7/15 | 2/5 | 2/5 | 273 | 11,60 s |
| C | 8/15 | 8/15 | 2/5 | 2/5 | 273 | Chung B |

## Audit trace

Codex chấm chunk đầu tiên chứa mốc giữa trang cho 10 trang PDF 17–26. Thang coherence 0–2 phản ánh mức độ giữ trọn ý. Điểm theo thứ tự trang:

- A: 1, 1, 1, 1, 2, 1, 1, 1, 1, 1. Trung bình 1,1. Phần lớn bị cắt ở biên; trang 21 giữ trọn định nghĩa tiền và tương đương tiền.
- B/C: 2, 2, 2, 2, 2, 2, 1, 1, 2, 2. Trung bình 1,8. Hai mẫu bị cắt là đoạn hợp đồng hợp tác (23) và đoạn về tiền thuê (24).

Mỗi cấu hình có 15/15 kết quả top-3 test khớp metadata của manifest và trang OCR. Kiểm tra source, document_id, page, printed_page, section và note_topic, đồng thời xác nhận text của chunk thuộc trang đó. Đây là kiểm tra với snapshot OCR. C tuân thủ filter 3/3 trên dev và 1/1 trên test; A và B lần lượt là 1/3 và 0/1.

| Câu test | A | B | C | Lý do chấm grounding |
|---|---:|---:|---:|---|
| q16 | 0 | 0 | 0 | Không tìm được đoạn hoàn nhập dự phòng bảo hành ở PDF 33. |
| q17 | 1 | 0 | 0 | A tìm đúng PDF 38 nhưng chunk cắt trước điều kiện hoàn thành nghĩa vụ. B/C trả PDF 42, 46, 54. |
| q18 | 2 | 2 | 2 | PDF 39 giữ điều kiện ghi nhận doanh thu theo chi phí có khả năng được hoàn trả. |
| q19 | 0 | 0 | 0 | Các đoạn phải thu và cho vay thiếu phân loại nợ xấu ở PDF 49. |
| q20 | 2 | 2 | 2 | PDF 55 giữ tỷ lệ vốn hóa 11,46%/năm. |
| Trung bình | 1,0 | 0,8 | 0,8 | Thang 0–2. |

## Diễn giải

B tăng Evidence Hit@3 trên dev từ 3/15 lên 7/15 và tăng coherence ở mẫu chấm. C tăng thêm một hit trên dev, nên được chọn theo tiêu chí đã chốt. C lọc đúng nhóm chính sách kế toán ở q16 nhưng bỏ lỡ trang 33. Test có 5 câu và cả ba cấu hình đạt 2/5. Kết quả giới hạn ở một báo cáo và chịu ảnh hưởng của lỗi OCR, ranh giới chunk và metadata cấp trang. Một thí nghiệm tiếp theo có thể giữ tiêu đề tiểu mục trong chunk và dùng bộ test mới.

Codex hỗ trợ rà OCR, soạn benchmark, viết pipeline, chạy thử và đề xuất nhãn từ trace thật. Người học chạy lại dev/test trên Windows. Trace đầy đủ sinh trong .day06-vic theo README và chứa văn bản OCR.
