# LexFlow Agent V2

Final integrated agent service for the Day 04 submission. Data/tool outputs use `contract_version=ver2`; artifact checkpoints v0–v3 remain available for evaluation evidence.

Start with [`../START-HERE.md`](../START-HERE.md). Tool/data details are in [`tools/LEGAL_TOOL_CONTRACT.md`](tools/LEGAL_TOOL_CONTRACT.md), while the report is [`artifacts/REPORT.md`](artifacts/REPORT.md).

Quick start on Windows PowerShell:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\preflight_provider.py --provider groq
.\.venv\Scripts\python.exe -m uvicorn api:app --port 8502
```

Set `GROQ_API_KEY` in this folder's `.env`. You may put multiple keys directly in that variable separated by commas, use comma-separated `GROQ_API_KEYS`, or use `GROQ_API_KEY_1`, `GROQ_API_KEY_2`, …. For backward compatibility, `gsk_` values in comma-separated `OPENROUTER_API_KEY` also join the Groq pool. Rotation occurs only for 429/quota/rate-limit errors; 401 requires replacing the invalid credential. Keys in one Groq organization may still share the same daily quota.

The chat header contains `V0`, `V1`, and `V2` buttons. Switching starts a clean local conversation. V0/V1 load historical prompt/tool artifacts; V2 is the integrated guarded OCR/RAG runtime.

Evaluation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\smoke_legal_tools.py
.\.venv\Scripts\python.exe run_eval.py --provider groq --version v3 --suite group --eval-cases data/eval_group.json
.\.venv\Scripts\python.exe run_eval.py --provider groq --version v3 --suite attack --eval-cases data/eval_attack_15.json
.\.venv\Scripts\python.exe scripts\compare_versions.py --provider groq
```

Do not submit `.env`, `.venv`, caches, build output, database/vector storage or private uploads.
