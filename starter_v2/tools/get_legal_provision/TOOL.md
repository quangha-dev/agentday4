# `get_legal_provision` Tool Specification

## Description
Lấy chính xác nguyên văn nội dung quy định pháp luật theo Mã/Số văn bản, Điều, Khoản, Điểm.
Ưu tiên sử dụng tool này khi người dùng đã cung cấp rõ cấu trúc Văn bản – Điều – Khoản – Điểm.

## Input Parameters
- `document_id` (string, required): Mã số hoặc định danh văn bản (ví dụ: `"ND_168_2024"`, `"168/2024/NĐ-CP"`).
- `article` (string, required): Số Điều (ví dụ: `"7"`).
- `clause` (string, optional): Số Khoản (ví dụ: `"7"`).
- `point` (string, optional): Ký tự Điểm (ví dụ: `"c"`).

## Output Schema
```json
{
  "tool": "get_legal_provision",
  "found": true,
  "document_id": "ND_168_2024",
  "document_number": "168/2024/NĐ-CP",
  "article": "7",
  "clause": "7",
  "point": "c",
  "content": "Xử phạt người điều khiển xe mô tô, xe gắn máy...",
  "effective_from": "2025-01-01",
  "effective_to": null,
  "source_url": "https://...",
  "page": 15
}
```

Nếu không tìm thấy:
```json
{
  "tool": "get_legal_provision",
  "found": false,
  "document_id": "ND_999_2099",
  "article": "99",
  "clause": null,
  "point": null,
  "message": "Không tìm thấy quy định tương ứng."
}
```

## Principles
1. Ưu tiên gọi trước `legal_rag_search` nếu thông tin đầu vào đã rõ ràng về Điều-Khoản-Điểm.
2. Trả về `found: false` khi không khớp chính xác, không được báo lỗi crash hệ thống hay bịa văn bản.
