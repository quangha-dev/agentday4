from __future__ import annotations

from pathlib import Path

import fitz
import numpy as np
from PIL import Image

from app.core.config import Settings


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


def _ocr_image(image: Image.Image, settings: Settings) -> tuple[str, float | None, list[dict]]:
    try:
        import pytesseract

        if settings.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
        prepared = _deskew(image)
        data = pytesseract.image_to_data(
            prepared,
            lang=settings.ocr_languages,
            config="--oem 3 --psm 6",
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
        text = pytesseract.image_to_string(prepared, lang=settings.ocr_languages, config="--oem 3 --psm 6")
        mean_confidence = sum(confidences) / len(confidences) if confidences else None
        return text.strip() or " ".join(words), mean_confidence, boxes
    except Exception as exc:
        raise RuntimeError(
            "Không thể chạy OCR. Hãy cài Tesseract cùng gói ngôn ngữ vie hoặc cấu hình TESSERACT_CMD."
        ) from exc


def extract_pdf(pdf_path: Path, image_root: Path, settings: Settings) -> list[dict]:
    document = fitz.open(pdf_path)
    results: list[dict] = []
    image_root.mkdir(parents=True, exist_ok=True)

    for index, page in enumerate(document):
        native_text = page.get_text("text").strip()
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False)
        image_path = image_root / f"page-{index + 1:04d}.png"
        pixmap.save(image_path)
        image = Image.open(image_path)

        if len(native_text) >= 80:
            classification = "native"
            text, confidence, boxes = native_text, 100.0, []
        else:
            text, confidence, boxes = _ocr_image(image, settings)
            classification = "hybrid" if native_text else "scanned"
            if native_text and len(native_text) > len(text):
                text = native_text

        results.append(
            {
                "page_number": index + 1,
                "classification": classification,
                "image_path": str(image_path.resolve()),
                "width": pixmap.width,
                "height": pixmap.height,
                "raw_text": text,
                "confidence": confidence,
                "bounding_boxes": boxes,
            }
        )
    document.close()
    return results

