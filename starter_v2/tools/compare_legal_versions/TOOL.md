# `compare_legal_versions` Tool Specification

## Description
So sánh quy định giữa văn bản cũ (`old_document_id`) và văn bản mới (`new_document_id`), phân tích chi tiết nội dung được sửa đổi (`modified`), thêm mới (`added`) hoặc bãi bỏ (`deleted`).

## Input Parameters
- `old_document_id` (string, required): Mã hoặc số hiệu văn bản quy định cũ (ví dụ: `"ND_100_2019"`).
- `new_document_id` (string, required): Mã hoặc số hiệu văn bản quy định mới (ví dụ: `"ND_168_2024"`).
- `article` (string, optional): Số Điều cần so sánh.
- `clause` (string, optional): Số Khoản cần so sánh.
- `point` (string, optional): Ký tự Điểm cần so sánh.

## Output Schema
```json
{
  "tool": "compare_legal_versions",
  "old_document_id": "ND_100_2019",
  "new_document_id": "ND_168_2024",
  "article": "7",
  "clause": "7",
  "point": "c",
  "old_content": "Phạt tiền từ 800.000 đồng đến 1.000.000 đồng...",
  "new_content": "Phạt tiền từ 4.000.000 đồng đến 6.000.000 đồng...",
  "changes": [
    {
      "type": "modified",
      "old_text": "800.000 đồng đến 1.000.000 đồng",
      "new_text": "4.000.000 đồng đến 6.000.000 đồng"
    }
  ],
  "summary": "Đã phát hiện 1 điểm thay đổi giữa quy định cũ và quy định mới.",
  "old_effective_to": "2024-12-31",
  "new_effective_from": "2025-01-01"
}
```

## Principles
1. Không tự so sánh chỉ bằng nội dung gần giống ghi nhớ của model; phải lấy đúng hai phiên bản văn bản thật.
2. Hiển thị rõ mốc thời gian hết hiệu lực của văn bản cũ và mốc có hiệu lực của văn bản mới.
