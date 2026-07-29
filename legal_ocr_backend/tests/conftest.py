from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4


# Pytest imports this file before test modules import app.main. Give the whole
# session isolated SQL/Qdrant/upload paths so a running local backend cannot lock
# the test store or receive test documents.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_RUNTIME = (PROJECT_ROOT / f".pytest-runtime-{uuid4().hex}").resolve()
TEST_RUNTIME.mkdir(parents=True, exist_ok=False)

os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_RUNTIME / 'test.db').as_posix()}"
os.environ["QDRANT_URL"] = ""
os.environ["QDRANT_PATH"] = str(TEST_RUNTIME / "qdrant")
os.environ["QDRANT_COLLECTION"] = "legal_provisions_ver2_test"
os.environ["UPLOAD_DIR"] = str(TEST_RUNTIME / "uploads")
os.environ["PAGE_IMAGE_DIR"] = str(TEST_RUNTIME / "page_images")
os.environ["EXPORT_DIR"] = str(TEST_RUNTIME / "exports")
os.environ["ENABLE_TRANSFORMER_EMBEDDING"] = "false"


def pytest_sessionfinish(session, exitstatus) -> None:
    del session, exitstatus
    try:
        from app.services.vector_store import get_vector_store

        if get_vector_store.cache_info().currsize:
            get_vector_store().client.close()
            get_vector_store.cache_clear()
    except Exception:
        pass

    # Safety check: cleanup only the unique test directory directly under this
    # project, never a user-selected or broad path.
    if TEST_RUNTIME.parent == PROJECT_ROOT and TEST_RUNTIME.name.startswith(".pytest-runtime-"):
        shutil.rmtree(TEST_RUNTIME, ignore_errors=True)
