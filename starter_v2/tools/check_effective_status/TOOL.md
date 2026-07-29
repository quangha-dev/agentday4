---
name: check_effective_status
version: ver2
kind: metadata_validation
side_effect: false
---

# check_effective_status ver2

Kiểm tra một document/version tại ngày ISO `target_date`. Input bắt buộc: `document_id`, `target_date`.

Status: `effective`, `not_yet_effective`, `replaced`, `unknown`, `unavailable`. Chỉ `effective` được dùng trong kết luận tại ngày đó. Tài liệu chưa INDEXED hoặc OCR thất bại trả `unavailable`/không được resolve.
