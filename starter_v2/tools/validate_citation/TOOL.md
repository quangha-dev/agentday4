---
name: validate_citation
version: ver2
kind: evidence_gate
side_effect: false
---

# validate_citation ver2

Gate cuối trước kết luận. Input: `claims[]` và `target_date`. Mỗi claim phải ngắn, nguyên tử, có đúng một `citation_id` lấy từ evidence.

Output: `valid`, `results[]`, `errors[]`. Mỗi result có `citation_exists`, `content_supported`, `term_coverage`, `effective_at_target_date`, `location_valid`, `valid`.

`valid=false` buộc tìm lại hoặc báo chưa đủ căn cứ; không phát hành claim bị từ chối.
