# LexFlow Frontend

Giao diện độc lập gồm khu chat và khu thư viện:

- `/`: chat gọi LexFlow Agent ver2 tại `NEXT_PUBLIC_AGENT_API_URL`, có tạo/xóa hội thoại và lưu lịch sử trên trình duyệt. Khi service lỗi, UI báo đúng trạng thái unavailable và không giả câu trả lời.
- `/library/upload`: nhập metadata, upload PDF, OCR, làm sạch LLM, đối chiếu PDF–text từng trang, xác nhận, tạo JSON và index vector.
- `/library/documents`: xem tài liệu đã thêm, version, cây Chương/Điều/Khoản/Điểm, tìm kiếm và mở đúng trang PDF nguồn.

```powershell
Copy-Item .env.example .env
npm install
npm run dev
```

Backend mặc định ở `http://localhost:8000/api/v1`. Có thể đổi bằng `NEXT_PUBLIC_API_URL`.
Agent mặc định ở `http://localhost:8502`. Có thể đổi bằng `NEXT_PUBLIC_AGENT_API_URL`.
