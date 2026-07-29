# `validate_citation` Tool Specification

## Description
Tool chốt chặn (Gatekeeper) xác thực bằng chứng pháp lý trước khi Agent đưa ra câu trả lời cuối cùng.
Kiểm tra đồng thời sự tồn tại của `citation_id`, nội dung điều khoản hỗ trợ cho khẳng định (`claim`), và thời gian hiệu lực tại `target_date`.

## Input Parameters
- `claims` (array of objects, required): Danh sách các khẳng định cần đối chiếu `[ { "claim": "...", "citation_id": "CIT_01" } ]`.
- `target_date` (string YYYY-MM-DD, required): Ngày áp dụng hiệu lực.
- `provisions` (array of objects, optional): Danh sách các điều khoản pháp lý đã thu thập từ các bước trước.

## Output Schema
```json
{
  "tool": "validate_citation",
  "valid": true,
  "target_date": "2026-07-29",
  "results": [
    {
      "claim": "Hành vi này bị phạt từ 4 đến 6 triệu đồng.",
      "citation_id": "CIT_01",
      "citation_exists": true,
      "content_supported": true,
      "effective_at_target_date": true,
      "location_valid": true,
      "valid": true
    }
  ],
  "errors": []
}
```

## Principles
1. Quy tắc bắt buộc: Nếu `valid = false`, Agent **tuyệt đối không được đưa ra kết luận cuối cùng** mà phải tìm kiếm lại hoặc báo chưa đủ căn cứ.
2. Kiểm tra chặt chẽ cả 3 yếu tố: Citation tồn tại + Nội dung khớp claim + Còn hiệu lực vào `target_date`.
