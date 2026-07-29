from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import get_settings
from app.core.database import SessionLocal, init_database
from app.services.mock_seed import seed_mock_document
from app.services.vector_store import get_vector_store


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Insert verified mock legal text directly into SQL and Qdrant, then run the "
            "production ver2 parser/chunker without OCR."
        )
    )
    parser.add_argument(
        "--query",
        default="thời hạn thông báo sự cố dữ liệu",
        help="Semantic query used to verify the new vectors",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Recreate only the deterministic MOCK fixture and its vector points",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()
    settings.ensure_directories()
    init_database()
    try:
        with SessionLocal() as db:
            payload = seed_mock_document(
                db,
                settings.mock_fixture_path,
                rebuild=args.rebuild,
                query=args.query,
            )
    except RuntimeError as exc:
        if "already accessed by another instance" in str(exc):
            print(
                "Qdrant local đang được backend sử dụng. Hãy dừng backend, chạy file seed "
                "này, rồi khởi động backend lại. Nếu dùng Qdrant server qua QDRANT_URL thì "
                "không có giới hạn khóa file này.",
                file=sys.stderr,
            )
            return 2
        raise
    except (OSError, ValueError) as exc:
        print(
            f"Mock seed thất bại: {exc}",
            file=sys.stderr,
        )
        return 1

    if get_vector_store.cache_info().currsize:
        get_vector_store().client.close()
        get_vector_store.cache_clear()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
