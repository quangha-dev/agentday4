# `extract_legal_information` Tool Specification

## Description
Trích xuất thông tin pháp lý có cấu trúc (Chủ thể, Hành vi, Quyền, Nghĩa vụ, Thời hạn, Mức phạt, Ngoại lệ) từ danh sách các điều khoản thô đã lấy từ tool RAG/Exact Lookup.

## Input Parameters
- `provisions` (array of objects, required): Danh sách các điều khoản pháp lý `[ { "citation_id": "CIT_01", "content": "..." } ]`.
- `fields` (array of strings, optional): Danh sách các trường cần trích xuất (`subject`, `conduct`, `rights`, `obligations`, `deadline`, `penalty`, `exceptions`).

## Output Schema
```json
{
  "tool": "extract_legal_information",
  "subject": "Người điều khiển xe mô tô, xe gắn máy",
  "conduct": "Không chấp hành tín hiệu đèn giao thông",
  "rights": [],
  "obligations": [],
  "deadline": null,
  "penalty": {
    "minimum": 4000000,
    "maximum": 6000000,
    "currency": "VND"
  },
  "exceptions": [],
  "evidence_ids": ["CIT_01"]
}
```

## Principles
1. Mọi trường thông tin được trích xuất phải gắn với danh sách `evidence_ids`.
2. Nếu không có thông tin thời hạn hoặc ngoại lệ, trả về `deadline: null` hoặc `exceptions: []`, tuyệt đối không tự bịa thông tin.
