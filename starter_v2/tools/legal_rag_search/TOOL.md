---
name: legal_rag_search
version: ver2
kind: hybrid_retrieval
side_effect: false
---

# legal_rag_search ver2

Dùng cho câu hỏi pháp luật tự nhiên hoặc chưa biết Điều/Khoản/Điểm. Không dùng thay exact lookup khi vị trí đã đầy đủ.

Input bắt buộc: `query`. Filter tùy chọn: `document_type`, `legal_domain`, `document_number`, `target_date`, `top_k`.

Output: `ok`, `count`, `evidence[]`, `retrieval`, `contract_version`. Mỗi evidence theo `LEGAL_TOOL_CONTRACT.md`. `count=0` nghĩa là không đủ căn cứ; không được suy đoán.

Lỗi hạ tầng trả `ok=false`, `error.code=legal_data_service_unavailable`, `evidence=[]`.
