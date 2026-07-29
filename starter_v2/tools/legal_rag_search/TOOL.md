# `legal_rag_search` Tool Specification

## Description
Tool chính để tìm các đoạn văn bản pháp luật liên quan bằng Hybrid Search (từ khóa + semantic score + metadata filtering).
Dùng khi câu hỏi sử dụng ngôn ngữ tự nhiên và chưa có mã Điều-Khoản-Điểm cụ thể.

## Input Parameters
- `query` (string, required): Câu hỏi hoặc từ khóa tra cứu pháp luật.
- `document_type` (string, optional): Loại văn bản (ví dụ: `"nghị định"`, `"luật"`, `"thông tư"`...). Mặc định `"all"`.
- `legal_domain` (string, optional): Lĩnh vực pháp luật (ví dụ: `"giao thông"`, `"dân sự"`, `"hình sự"`...). Mặc định `"all"`.
- `target_date` (string YYYY-MM-DD, optional): Ngày cần áp dụng hiệu lực.
- `top_k` (integer, optional): Số lượng đoạn văn bản tối đa trả về (mặc định 5).

## Output Schema
```json
{
  "tool": "legal_rag_search",
  "query": "Mức phạt khi vượt đèn đỏ bằng xe máy?",
  "document_type": "nghị định",
  "legal_domain": "giao thông",
  "target_date": "2026-07-29",
  "results": [
    {
      "document_id": "ND_168_2024",
      "document_number": "168/2024/NĐ-CP",
      "article": "7",
      "clause": "7",
      "point": "c",
      "content": "Nội dung nguyên văn...",
      "effective_from": "2025-01-01",
      "effective_to": null,
      "source_url": "https://...",
      "score": 0.91
    }
  ],
  "trust_boundary": "..."
}
```

## Principles
1. Không dùng kết quả chỉ vì score cao; bắt buộc kiểm tra hiệu lực với `check_effective_status`.
2. Nếu không tìm thấy kết quả phù hợp, trả về `results: []`. Không bao giờ bịa nội dung.
