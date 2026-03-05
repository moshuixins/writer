from __future__ import annotations

from pathlib import Path

try:
    from PIL import ImageEnhance, ImageFilter
except Exception:  # pragma: no cover
    ImageEnhance = None
    ImageFilter = None

from PyPDF2 import PdfReader

try:
    from pdf2image import convert_from_path
except Exception:  # pragma: no cover
    convert_from_path = None

try:
    from pytesseract import image_to_string
except Exception:  # pragma: no cover
    image_to_string = None

from app.config import get_settings
from app.errors import FileValidationError, logger

settings = get_settings()
OCR_BATCH_PAGES = 8


class PdfOcrService:
    """PDF parser with text-layer extraction and OCR fallback."""

    @staticmethod
    def _preprocess_image(image):
        if ImageEnhance is None or ImageFilter is None:
            raise FileValidationError("Pillow dependency missing for OCR preprocessing")
        gray = image.convert("L")
        enhanced = ImageEnhance.Contrast(gray).enhance(2.0)
        denoised = enhanced.filter(ImageFilter.MedianFilter(size=3))
        return denoised.filter(ImageFilter.SHARPEN)

    @staticmethod
    def _normalize_page_text(text: str) -> str:
        if not text:
            return ""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "\n".join(lines).strip()

    def _extract_text_layer(self, file_path: str) -> dict[str, object]:
        try:
            reader = PdfReader(file_path)
        except Exception as e:
            raise FileValidationError("PDF 文件损坏或已加密") from e

        page_texts: list[str] = []
        non_empty_pages = 0

        for page in reader.pages:
            text = ""
            try:
                text = page.extract_text() or ""
            except Exception as e:
                logger.warning("PDF text extraction warning: %s", e)
            clean = self._normalize_page_text(text)
            if clean:
                non_empty_pages += 1
            page_texts.append(clean)

        total_pages = len(page_texts)
        total_chars = sum(len(page_text) for page_text in page_texts)
        non_empty_ratio = (non_empty_pages / total_pages) if total_pages else 0.0

        chapters = [
            {
                "chapter_title": f"Page {idx + 1}",
                "text": page_text,
                "page_start": idx + 1,
                "page_end": idx + 1,
            }
            for idx, page_text in enumerate(page_texts)
            if page_text
        ]

        return {
            "chapters": chapters,
            "total_pages": total_pages,
            "total_chars": total_chars,
            "non_empty_pages": non_empty_pages,
            "non_empty_ratio": non_empty_ratio,
        }

    def _extract_ocr(self, file_path: str, total_pages: int) -> dict[str, object]:
        if not settings.pdf_ocr_enabled:
            return {
                "chapters": [],
                "ocr_pages": 0,
                "ocr_used": False,
                "warning": "ocr_disabled",
            }
        if convert_from_path is None or image_to_string is None:
            raise FileValidationError("OCR dependency missing: pdf2image + pytesseract + poppler + tesseract")

        ocr_pages_limit = min(max(total_pages, 0), max(int(settings.pdf_ocr_max_pages), 0))
        if ocr_pages_limit <= 0:
            return {
                "chapters": [],
                "ocr_pages": 0,
                "ocr_used": False,
                "warning": "ocr_pages_limit_zero",
            }

        chapters: list[dict[str, object]] = []
        ocr_pages = 0
        batch_size = max(1, OCR_BATCH_PAGES)

        for start_page in range(1, ocr_pages_limit + 1, batch_size):
            end_page = min(start_page + batch_size - 1, ocr_pages_limit)
            images = []
            try:
                images = convert_from_path(
                    file_path,
                    dpi=int(settings.pdf_ocr_dpi),
                    first_page=start_page,
                    last_page=end_page,
                )
            except Exception as e:
                logger.warning("PDF OCR batch conversion failed: pages=%s-%s err=%s", start_page, end_page, e)
                continue

            try:
                for offset, image in enumerate(images):
                    page_no = start_page + offset
                    try:
                        processed = self._preprocess_image(image)
                        text = image_to_string(processed, lang=settings.pdf_ocr_lang or "chi_sim+eng")
                        clean = self._normalize_page_text(text)
                    except Exception as e:
                        logger.warning("PDF OCR warning: page=%s err=%s", page_no, e)
                        continue

                    ocr_pages += 1
                    if not clean:
                        continue
                    chapters.append(
                        {
                            "chapter_title": f"Page {page_no}",
                            "text": clean,
                            "page_start": page_no,
                            "page_end": page_no,
                        },
                    )
            finally:
                for image in images:
                    try:
                        image.close()
                    except Exception:
                        pass

        return {
            "chapters": chapters,
            "ocr_pages": ocr_pages,
            "ocr_used": True,
            "warning": "",
        }

    def parse_pdf(self, file_path: str) -> dict[str, object]:
        path = Path(file_path)
        if not path.exists():
            raise FileValidationError("PDF 文件不存在")

        text_layer = self._extract_text_layer(file_path)
        total_chars = int(text_layer["total_chars"])
        non_empty_ratio = float(text_layer["non_empty_ratio"])
        total_pages = int(text_layer["total_pages"])

        should_ocr = total_chars < 200 or non_empty_ratio < 0.3
        if should_ocr and settings.pdf_ocr_enabled:
            ocr_result = self._extract_ocr(file_path, total_pages=total_pages)
            chapters = ocr_result.get("chapters", []) or []
            if chapters:
                return {
                    "chapters": chapters,
                    "ocr_used": bool(ocr_result.get("ocr_used", False)),
                    "ocr_pages": int(ocr_result.get("ocr_pages", 0)),
                    "total_pages": total_pages,
                    "text_layer_chars": total_chars,
                    "non_empty_ratio": non_empty_ratio,
                }
            logger.warning("OCR produced no content, fallback to text-layer output")

        return {
            "chapters": text_layer["chapters"],
            "ocr_used": False,
            "ocr_pages": 0,
            "total_pages": total_pages,
            "text_layer_chars": total_chars,
            "non_empty_ratio": non_empty_ratio,
        }
