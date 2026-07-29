# Analysis outputs

Tạo CSV base runs bằng:

```powershell
.\.venv\Scripts\python.exe scripts\parse_runs.py runs\ --output analysis\base_runs.csv
```

So sánh V0/V1/V2 trên 15 adversarial cases bằng:

```powershell
.\.venv\Scripts\python.exe scripts\compare_versions.py --provider groq
```

Script thứ hai tự ghi `analysis/attack_15_comparison_<timestamp>.csv`. Không điền metric thủ công khi provider có lỗi.
