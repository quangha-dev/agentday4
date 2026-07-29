---
name: extract_legal_information
version: ver2
kind: citation_backed_extraction
side_effect: false
---

# extract_legal_information ver2

Input chỉ gồm `citation_ids` đã lấy từ retrieval và `fields`. Backend tự đọc nguyên văn theo ID; model không được truyền content.

Field hợp lệ: `subject`, `conduct`, `rights`, `obligations`, `deadline`, `penalty`, `exceptions`.

Output giữ `evidence_ids`. Citation không tồn tại trả `ok=false`, `error.code=citation_not_found`; không trích xuất từ nội dung user/model tự soạn.
