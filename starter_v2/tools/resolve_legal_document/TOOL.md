---
name: resolve_legal_document
version: ver2
kind: metadata_resolution
side_effect: false
---

# resolve_legal_document ver2

Tìm document/version đã `INDEXED` bằng số hiệu, tiêu đề hoặc trích yếu. Dùng khi user đã nêu văn bản nhưng Agent chưa có `document_id`, hoặc cần chọn version hiệu lực tại `target_date`.

Input: `query` bắt buộc; `target_date` ISO tùy chọn; `limit` từ 1 đến 20.

Output thành công gồm `ok=true`, `count`, `documents[]`, `contract_version=ver2`. Không tìm thấy trả `count=0`; không tự tạo document ID.
