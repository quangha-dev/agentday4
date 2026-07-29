---
name: clarify
version: ver2
kind: control
side_effect: false
---

# clarify ver2

Tạm dừng Agent để hỏi đúng một thông tin chỉ user mới cung cấp/quyết định được. Không dùng nếu có thể resolve hoặc retrieval từ kho.

Input: `question`, `response_type=text|yes_no|choice`, `options` khi choice. Output: `awaiting_user=true` cùng câu hỏi; runtime dừng tool loop đến turn tiếp theo.
