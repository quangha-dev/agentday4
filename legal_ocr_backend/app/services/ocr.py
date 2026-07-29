from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import fitz
import numpy as np
from PIL import Image

from app.core.config import Settings


class OcrError(RuntimeError):
    def __init__(self, code: str, message: str, *, page_number: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.page_number = page_number


def _tesseract_executable(settings: Settings) -> str | None:
    if settings.tesseract_cmd:
        configured = Path(settings.tesseract_cmd)
        return str(configured) if configured.is_file() else None
    return shutil.which("tesseract")


def _tessdata_args(settings: Settings) -> list[str]:
    if settings.tessdata_dir:
        return ["--tessdata-dir", str(settings.tessdata_dir)]
    return []


def ocr_readiness(settings: Settings) -> dict:
    executable = _tesseract_executable(settings)
    required_languages = [item.strip() for item in settings.ocr_languages.split("+") if item.strip()]
    if not executable:
        return {
            "contract_version": settings.contract_version,
            "ready": False,
            "engine": "tesseract",
            "executable": settings.tesseract_cmd,
            "required_languages": required_languages,
            "available_languages": [],
            "error": {
                "code": "tesseract_not_found",
                "message": "Không tìm thấy Tesseract. Hãy cấu hình TESSERACT_CMD hoặc chạy backend bằng Docker.",
            },
        }

    try:
        completed = subprocess.run(
            [executable, *_tessdata_args(settings), "--list-langs"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
        available = sorted(
            line.strip()
            for line in (completed.stdout + "\n" + completed.stderr).splitlines()
            if line.strip() and not line.casefold().startswith("list of available languages")
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "contract_version": settings.contract_version,
            "ready": False,
            "engine": "tesseract",
            "executable": executable,
            "required_languages": required_languages,
            "available_languages": [],
            "error": {"code": "tesseract_probe_failed", "message": str(exc)},
        }

    missing = sorted(set(required_languages) - set(available))
    return {
        "contract_version": settings.contract_version,
        "ready": not missing,
        "engine": "tesseract",
        "executable": executable,
        "tessdata_dir": str(settings.tessdata_dir) if settings.tessdata_dir else None,
        "required_languages": required_languages,
        "available_languages": available,
        "error": (
            {
                "code": "ocr_language_missing",
                "message": "Thiếu language pack: " + ", ".join(missing),
                "missing_languages": missing,
            }
            if missing
            else None
        ),
    }


def _deskew(image: Image.Image) -> Image.Image:
    try:
        import cv2

        array = np.array(image.convert("L"))
        inverted = cv2.bitwise_not(array)
        coordinates = np.column_stack(np.where(inverted > 0))
        if len(coordinates) < 50:
            return image
        angle = cv2.minAreaRect(coordinates)[-1]
        angle = -(90 + angle) if angle < -45 else -angle
        if abs(angle) < 0.15 or abs(angle) > 10:
            return image
        height, width = array.shape
        matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
        rotated = cv2.warpAffine(
            array, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        return Image.fromarray(rotated)
    except Exception:
        return image


def _ocr_image(
    image: Image.Image,
    settings: Settings,
    *,
    page_number: int,
) -> tuple[str, float | None, list[dict]]:
    import pytesseract

    executable = _tesseract_executable(settings)
    if not executable:
        raise OcrError(
            "tesseract_not_found",
            "Không tìm thấy Tesseract OCR.",
            page_number=page_number,
        )
    pytesseract.pytesseract.tesseract_cmd = executable
    prepared = _deskew(image)
    tessdata_path = settings.tessdata_dir.as_posix() if settings.tessdata_dir else None
    if tessdata_path and any(character.isspace() for character in tessdata_path):
        raise OcrError(
            "invalid_tessdata_path",
            "TESSDATA_DIR không được chứa khoảng trắng khi chạy qua pytesseract trên Windows.",
            page_number=page_number,
        )
    tessdata_config = f" --tessdata-dir {tessdata_path}" if tessdata_path else ""
    config = f"--oem 1 --psm 6{tessdata_config}"
    try:
        data = pytesseract.image_to_data(
            prepared,
            lang=settings.ocr_languages,
            config=config,
            output_type=pytesseract.Output.DICT,
        )
        boxes: list[dict] = []
        words: list[str] = []
        confidences: list[float] = []
        for index, raw_word in enumerate(data.get("text", [])):
            word = raw_word.strip()
            try:
                confidence = float(data["conf"][index])
            except (TypeError, ValueError):
                confidence = -1
            if not word:
                continue
            words.append(word)
            if confidence >= 0:
                confidences.append(confidence)
            boxes.append(
                {
                    "text": word,
                    "confidence": confidence,
                    "x": int(data["left"][index]),
                    "y": int(data["top"][index]),
                    "width": int(data["width"][index]),
                    "height": int(data["height"][index]),
                    "block": int(data["block_num"][index]),
                    "line": int(data["line_num"][index]),
                }
            )
        text = pytesseract.image_to_string(
            prepared,
            lang=settings.ocr_languages,
            config=config,
        )
        mean_confidence = sum(confidences) / len(confidences) if confidences else None
        return text.strip() or " ".join(words), mean_confidence, boxes
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrError(
            "tesseract_not_found",
            "Không tìm thấy Tesseract OCR.",
            page_number=page_number,
        ) from exc
    except pytesseract.TesseractError as exc:
        message = str(exc)
        code = "ocr_language_missing" if "Failed loading language" in message else "page_ocr_failed"
        raise OcrError(code, message, page_number=page_number) from exc


PageCallback = Callable[[dict, int, int], None]


def extract_pdf(
    pdf_path: Path,
    image_root: Path,
    settings: Settings,
    *,
    on_page: PageCallback | None = None,
) -> list[dict]:
    try:
        document = fitz.open(pdf_path)
    except Exception as exc:
        raise OcrError("pdf_open_failed", "Không thể mở PDF nguồn.") from exc

    results: list[dict] = []
    image_root.mkdir(parents=True, exist_ok=True)
    readiness_checked = False
    try:
        total_pages = len(document)
        for index, page in enumerate(document):
            page_number = index + 1
            native_text = page.get_text("text").strip()
            try:
                pixmap = page.get_pixmap(
                    matrix=fitz.Matrix(settings.ocr_dpi_scale, settings.ocr_dpi_scale),
                    alpha=False,
                )
                image_path = image_root / f"page-{page_number:04d}.png"
                pixmap.save(image_path)
                with Image.open(image_path) as opened:
                    image = opened.copy()
            except Exception as exc:
                raise OcrError(
                    "page_render_failed",
                    f"Không thể render trang {page_number}.",
                    page_number=page_number,
                ) from exc

            if len(native_text) >= 80:
                classification = "native"
                text, confidence, boxes = native_text, 100.0, []
                engine = "pymupdf"
            else:
                if not readiness_checked:
                    readiness = ocr_readiness(settings)
                    readiness_checked = True
                    if not readiness["ready"]:
                        error = readiness.get("error") or {}
                        raise OcrError(
                            error.get("code", "ocr_not_ready"),
                            error.get("message", "OCR chưa sẵn sàng."),
                            page_number=page_number,
                        )
                text, confidence, boxes = _ocr_image(image, settings, page_number=page_number)
                classification = "hybrid" if native_text else "scanned"
                engine = "tesseract"
                if native_text and len(native_text) > len(text):
                    text, engine = native_text, "pymupdf"

            result = {
                "page_number": page_number,
                "classification": classification,
                "image_path": str(image_path.resolve()),
                "width": pixmap.width,
                "height": pixmap.height,
                "raw_text": text,
                "confidence": confidence,
                "bounding_boxes": boxes,
                "ocr_engine": engine,
                "ocr_languages": settings.ocr_languages if engine == "tesseract" else None,
            }
            results.append(result)
            if on_page:
                on_page(result, page_number, total_pages)
    finally:
        document.close()
    return results
