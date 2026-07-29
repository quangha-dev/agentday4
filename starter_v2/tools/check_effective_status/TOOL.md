# `check_effective_status` Tool Specification

## Description
Xác định văn bản hoặc điều khoản pháp luật có hiệu lực tại thời điểm `target_date` được hỏi hay không.
Bắt buộc gọi tool này sau khi tìm thấy văn bản để kiểm tra xem văn bản còn hiệu lực, hết hiệu lực hay đã bị thay thế.

## Input Parameters
- `document_id` (string, required): Mã hoặc số hiệu văn bản (ví dụ: `"ND_168_2024"`, `"168/2024/NĐ-CP"`).
- `target_date` (string YYYY-MM-DD, required): Ngày cần áp dụng hiệu lực.
- `article` (string, optional): Số Điều cần kiểm tra.
- `clause` (string, optional): Số Khoản cần kiểm tra.
- `point` (string, optional): Ký tự Điểm cần kiểm tra.

## Output Schema
```json
{
  "tool": "check_effective_status",
  "document_id": "ND_168_2024",
  "document_number": "168/2024/NĐ-CP",
  "target_date": "2026-07-29",
  "status": "effective",
  "effective_from": "2025-01-01",
  "effective_to": null,
  "amended_by": [],
  "replaced_by": null,
  "notes": "Văn bản đang có hiệu lực tại thời điểm 2026-07-29."
}
```

Trạng thái chuẩn của `status`:
- `not_yet_effective`
- `effective`
- `partially_effective`
- `expired`
- `replaced`
- `unknown`

## Principles
1. Không dùng văn bản có trạng thái `expired`, `replaced` hoặc `not_yet_effective` để làm căn cứ pháp lý hiện hành.
2. Nếu trạng thái là `unknown`, không được khẳng định kết quả chắc chắn.
