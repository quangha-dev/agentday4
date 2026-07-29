# Live transcripts

Sau khi provider preflight PASS, chạy:

```powershell
.\.venv\Scripts\python.exe chat.py --provider groq --version v3
```

Thực hiện ít nhất ba scenario trong `TEST-QUESTIONS.md`. CLI tự tạo `*.transcript.json`, lưu tool rounds/results/error và redaction nhưng không lưu secret.
