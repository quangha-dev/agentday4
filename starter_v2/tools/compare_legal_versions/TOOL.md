---
name: compare_legal_versions
version: ver2
kind: version_comparison
side_effect: false
---

# compare_legal_versions ver2

Chỉ dùng khi user yêu cầu so sánh. Input bắt buộc: `old_document_id`, `new_document_id`; vị trí Điều/Khoản/Điểm tùy chọn. Cả hai selector phải rõ ràng, không đoán.

Output: `old_document`, `new_document`, `old_found`, `new_found`, `changes[]`, `evidence[]`. `changes[].type` là `added`, `modified` hoặc `deleted`.
