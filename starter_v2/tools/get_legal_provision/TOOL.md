---
name: get_legal_provision
version: ver2
kind: exact_retrieval
side_effect: false
---

# get_legal_provision ver2

Lấy đúng một Điều/Khoản/Điểm từ tài liệu đã `INDEXED`. Input: `document_id` và `article` bắt buộc; `clause`, `point` tùy chọn. `document_id` nhận UUID, số hiệu, tiêu đề hoặc `<số-hiệu>@vN`.

Thành công có `found=true`, `evidence=[...]`. Không tồn tại trả `found=false`, `evidence=[]`; không tự nới lỏng vị trí.
