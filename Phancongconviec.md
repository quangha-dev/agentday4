và hướng đẫn system promt cho role viết nó và các test case cần thiết 
1. Bộ tool cho Legal Search Agent
Tool 1 — legal_rag_search

Tác dụng: Tool chính để tìm các đoạn pháp luật liên quan bằng hybrid search: từ khóa + semantic search + metadata.

Đầu vào

{
  "query": "Mức phạt khi vượt đèn đỏ bằng xe máy?",
  "document_type": "nghị định",
  "legal_domain": "giao thông",
  "target_date": "2026-07-29",
  "top_k": 5
}

Đầu ra

{
  "results": [
    {
      "document_id": "ND_168_2024",
      "document_number": "168/2024/NĐ-CP",
      "article": "7",
      "clause": "7",
      "point": "c",
      "content": "Nội dung điều khoản...",
      "effective_from": "2025-01-01",
      "effective_to": null,
      "source_url": "...",
      "score": 0.91
    }
  ]
}

Nguyên tắc: Không dùng kết quả chỉ vì điểm tương đồng cao; phải kiểm tra hiệu lực và citation.

Tool 2 — get_legal_provision

Tác dụng: Lấy chính xác nội dung theo Văn bản – Điều – Khoản – Điểm.

Đầu vào

{
  "document_id": "ND_168_2024",
  "article": "7",
  "clause": "7",
  "point": "c"
}

Đầu ra

{
  "found": true,
  "document_number": "168/2024/NĐ-CP",
  "article": "7",
  "clause": "7",
  "point": "c",
  "content": "Nội dung nguyên văn...",
  "source_url": "...",
  "page": 15
}

Nguyên tắc: Ưu tiên tool này khi người dùng đã cung cấp rõ Điều–Khoản–Điểm.

Tool 3 — check_effective_status

Tác dụng: Xác định văn bản hoặc điều khoản có hiệu lực tại thời điểm được hỏi.

Đầu vào

{
  "document_id": "ND_168_2024",
  "target_date": "2026-07-29"
}

Đầu ra

{
  "status": "effective",
  "effective_from": "2025-01-01",
  "effective_to": null,
  "amended_by": [],
  "replaced_by": null,
  "notes": null
}

Trạng thái chuẩn:

not_yet_effective
effective
partially_effective
expired
replaced
unknown
Tool 4 — compare_legal_versions

Tác dụng: So sánh quy định cũ và mới, xác định nội dung thêm, sửa hoặc bãi bỏ.

Đầu vào

{
  "old_document_id": "OLD_DOCUMENT",
  "new_document_id": "NEW_DOCUMENT",
  "article": "7",
  "clause": "7",
  "point": "c"
}

Đầu ra

{
  "old_content": "...",
  "new_content": "...",
  "changes": [
    {
      "type": "modified",
      "old_text": "...",
      "new_text": "..."
    }
  ],
  "summary": "Mức phạt đã được thay đổi...",
  "old_effective_to": "2024-12-31",
  "new_effective_from": "2025-01-01"
}
Tool 5 — extract_legal_information

Tác dụng: Trích xuất thông tin pháp lý có cấu trúc từ các điều khoản đã tìm được.

Đầu vào

{
  "provisions": [
    {
      "citation_id": "CIT_01",
      "content": "Nội dung điều khoản..."
    }
  ],
  "fields": [
    "subject",
    "conduct",
    "rights",
    "obligations",
    "deadline",
    "penalty",
    "exceptions"
  ]
}

Đầu ra

{
  "subject": "Người điều khiển xe mô tô",
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

Nguyên tắc: Mọi trường được trích xuất phải gắn với evidence_ids.

Tool 6 — validate_citation

Tác dụng: Kiểm tra bằng chứng trước khi Agent trả lời.

Đầu vào

{
  "claims": [
    {
      "claim": "Hành vi này bị phạt từ 4 đến 6 triệu đồng.",
      "citation_id": "CIT_01"
    }
  ],
  "target_date": "2026-07-29"
}

Đầu ra

{
  "valid": true,
  "results": [
    {
      "claim": "Hành vi này bị phạt từ 4 đến 6 triệu đồng.",
      "citation_exists": true,
      "content_supported": true,
      "effective_at_target_date": true,
      "location_valid": true
    }
  ],
  "errors": []
}

Quy tắc bắt buộc: Nếu valid = false, Agent không được đưa ra kết luận cuối cùng.

2. Thứ tự gọi tool
Người dùng nhập câu hỏi
        ↓
Có Điều–Khoản–Điểm rõ ràng?
   ├─ Có → get_legal_provision
   └─ Không → legal_rag_search
        ↓
check_effective_status
        ↓
Có yêu cầu so sánh?
   └─ Có → compare_legal_versions
        ↓
extract_legal_information
        ↓
validate_citation
        ↓
Trả lời hoặc tìm kiếm lại

Agent chỉ nên tìm lại tối đa 3 vòng để tránh loop.

3. Hướng dẫn cho người viết Role và System Prompt

Người phụ trách prompt cần quy định rõ:

Vai trò: Agent hỗ trợ tra cứu, không đóng vai luật sư.
Mục tiêu: Tìm đúng quy định đang có hiệu lực tại thời điểm người dùng hỏi.
Quy tắc chọn tool: Exact search trước, RAG sau.
Quy tắc bằng chứng: Không kết luận nếu chưa có citation hợp lệ.
Quy tắc thời gian: Luôn kiểm tra ngày hiệu lực.
Quy tắc so sánh: Không so sánh chỉ bằng nội dung gần giống; phải lấy đúng hai phiên bản.
Quy tắc chống hallucination: Không tự tạo số hiệu, Điều, Khoản, mức phạt hoặc thời hạn.
Quy tắc dừng: Tối đa 3 vòng tìm kiếm.
Định dạng đầu ra: Kết luận, căn cứ, hiệu lực, so sánh và lưu ý.
System prompt mẫu

Bạn là Legal Search Agent, có nhiệm vụ tra cứu và tổng hợp thông tin từ kho văn bản pháp luật đã được cung cấp.

MỤC TIÊU

Trả lời câu hỏi pháp luật dựa trên đúng văn bản, Điều, Khoản và Điểm; xác định hiệu lực tại thời điểm người dùng hỏi; cung cấp citation có thể kiểm chứng.

QUY TẮC HOẠT ĐỘNG

Không sử dụng kiến thức ghi nhớ của mô hình làm căn cứ pháp lý.
Không tự tạo số hiệu văn bản, Điều, Khoản, Điểm, mức phạt, thời hạn hoặc trạng thái hiệu lực.
Khi người dùng cung cấp rõ số hiệu hoặc Điều–Khoản–Điểm, gọi get_legal_provision trước.
Khi câu hỏi dùng ngôn ngữ tự nhiên, gọi legal_rag_search.
Sau khi tìm được văn bản, luôn gọi check_effective_status với ngày người dùng yêu cầu.
Nếu người dùng không cung cấp ngày, sử dụng ngày hiện tại của hệ thống và nêu rõ ngày đã dùng.
Khi người dùng yêu cầu so sánh quy định cũ và mới, gọi compare_legal_versions.
Chỉ gọi extract_legal_information trên các điều khoản đã lấy từ tool.
Mọi kết luận pháp lý phải có citation tương ứng.
Trước khi trả lời cuối cùng, bắt buộc gọi validate_citation.
Nếu citation không hợp lệ, tìm kiếm lại với truy vấn khác.
Không tìm kiếm quá 3 vòng. Sau 3 vòng mà chưa đủ bằng chứng, thông báo chưa đủ căn cứ.
Không suy diễn vượt quá nội dung văn bản.
Khi nguồn có mâu thuẫn hoặc trạng thái hiệu lực là unknown, không đưa ra kết luận chắc chắn.
Không đưa ra lời khuyên mang tính đại diện pháp lý hoặc cam kết kết quả tranh chấp.

ĐỊNH DẠNG TRẢ LỜI

Kết luận:
Trả lời trực tiếp và ngắn gọn.

Căn cứ pháp lý:

Điểm, Khoản, Điều.
Tên và số hiệu văn bản.
Nội dung liên quan.
Trạng thái hiệu lực tại ngày được hỏi.
Nguồn trích dẫn.

So sánh:
Chỉ hiển thị khi người dùng yêu cầu, gồm quy định cũ, quy định mới và thay đổi chính.

Lưu ý:
Nếu dữ liệu chưa đủ, nói rõ chưa đủ căn cứ và không suy đoán.

4. Test case cần thiết
A. Test từng tool
ID	Tool	Trường hợp kiểm thử	Kết quả mong đợi
T01	legal_rag_search	Câu hỏi đúng lĩnh vực	Trả về điều khoản liên quan trong top 5
T02	legal_rag_search	Câu hỏi không có trong dữ liệu	Trả danh sách rỗng, không tạo nội dung
T03	legal_rag_search	Có ngày áp dụng	Không ưu tiên văn bản ngoài thời gian yêu cầu
T04	get_legal_provision	Điều–Khoản–Điểm tồn tại	Trả đúng nguyên văn và metadata
T05	get_legal_provision	Điều không tồn tại	found = false
T06	check_effective_status	Văn bản còn hiệu lực	Trả effective
T07	check_effective_status	Văn bản hết hiệu lực	Trả expired và văn bản thay thế nếu có
T08	compare_legal_versions	Có nội dung thay đổi	Phân loại đúng thêm, sửa, bỏ
T09	extract_legal_information	Có mức phạt	Trích đúng min, max và đơn vị
T10	extract_legal_information	Không có thời hạn	Trả deadline = null
T11	validate_citation	Citation hỗ trợ kết luận	valid = true
T12	validate_citation	Citation sai điều khoản	valid = false
B. Test hành vi Agent
ID	Đầu vào	Kết quả mong đợi
A01	“Khoản 2 Điều 10 của văn bản X quy định gì?”	Gọi get_legal_provision trước
A02	“Vượt đèn đỏ bị phạt bao nhiêu?”	Gọi legal_rag_search
A03	Hỏi quy định tại năm 2023	Kiểm tra hiệu lực đúng ngày năm 2023
A04	Hỏi quy định hiện hành	Dùng ngày hiện tại và nêu rõ ngày
A05	Hỏi so sánh cũ và mới	Gọi compare_legal_versions
A06	RAG trả văn bản hết hiệu lực	Không dùng làm kết luận hiện hành
A07	Citation không hỗ trợ mức phạt	Tìm lại, không trả lời ngay
A08	Sau 3 vòng vẫn không tìm thấy	Dừng và báo chưa đủ căn cứ
A09	Người dùng yêu cầu Agent tự đoán	Từ chối suy đoán
A10	Hai văn bản có kết quả mâu thuẫn	Nêu mâu thuẫn, không kết luận chắc chắn
C. Test end-to-end
E01 — Tìm kiếm tự nhiên

Đầu vào: “Người đi xe máy vượt đèn đỏ bị xử phạt thế nào?”

Mong đợi:

Tìm đúng lĩnh vực.
Có Điều–Khoản–Điểm.
Có mức phạt.
Văn bản còn hiệu lực.
Citation hợp lệ.
E02 — Tra cứu chính xác

Đầu vào: “Điểm c Khoản 7 Điều 7 của văn bản X quy định gì?”

Mong đợi:

Không cần semantic search trước.
Trả đúng nguyên văn.
Citation đúng vị trí.
E03 — So sánh phiên bản

Đầu vào: “Mức phạt năm 2024 khác năm 2026 thế nào?”

Mong đợi:

Lấy đúng hai phiên bản.
Hiển thị ngày hiệu lực.
Chỉ rõ nội dung tăng, giảm hoặc thay đổi.
E04 — Không đủ dữ liệu

Đầu vào: Câu hỏi về lĩnh vực chưa được ingest.

Mong đợi:

Không bịa câu trả lời.
Thông báo chưa tìm thấy đủ căn cứ.
Ghi lại trace tìm kiếm.
5. Tiêu chí nghiệm thu

Hệ thống được coi là đạt khi:

Exact search đúng Điều–Khoản–Điểm: ≥ 95%.
Điều khoản đúng nằm trong top 5 của RAG: ≥ 90%.
Kiểm tra hiệu lực đúng: 100% trên bộ test.
Citation khớp nội dung: ≥ 95%.
Không tạo citation giả: 100%.
Agent không vượt quá 3 vòng tìm kiếm.
Mọi câu trả lời có căn cứ đều truy ngược được về nguồn. 