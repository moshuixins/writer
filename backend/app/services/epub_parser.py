from __future__ import annotations

from pathlib import Path

try:
    from bs4 import BeautifulSoup
    from ebooklib import ITEM_DOCUMENT, epub
except Exception:  # pragma: no cover - fallback path for optional deps
    BeautifulSoup = None
    ITEM_DOCUMENT = None
    epub = None

from app.errors import FileValidationError, logger


class EpubParser:
    """Parse EPUB into chapter-level plain text."""

    def parse(self, file_path: str) -> list[dict[str, str]]:
        if epub is None or BeautifulSoup is None or ITEM_DOCUMENT is None:
            raise FileValidationError("EPUB parser dependency missing: install ebooklib + beautifulsoup4")

        path = Path(file_path)
        if not path.exists():
            raise FileValidationError(f"EPUB file not found: {file_path}")

        try:
            book = epub.read_epub(str(path))
        except Exception as e:
            raise FileValidationError(f"EPUB parsing failed: {e}")

        chapters: list[dict[str, str]] = []
        chapter_index = 0

        for item in book.get_items_of_type(ITEM_DOCUMENT):
            chapter_index += 1
            try:
                soup = BeautifulSoup(item.get_content(), "html.parser")
            except Exception as e:
                logger.warning("EPUB chapter parse warning (%s): %s", item.get_name(), e)
                continue

            for tag in soup(["script", "style"]):
                tag.decompose()

            title_node = soup.find(["h1", "h2", "h3", "title"])
            chapter_title = ""
            if title_node and title_node.get_text(strip=True):
                chapter_title = title_node.get_text(strip=True)
            if not chapter_title:
                chapter_title = f"Chapter {chapter_index}"

            text = soup.get_text("\n", strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            clean_text = "\n".join(lines).strip()

            if not clean_text:
                logger.warning("EPUB chapter has empty text: %s", item.get_name())
                continue

            chapters.append(
                {
                    "chapter_title": chapter_title[:200],
                    "text": clean_text,
                },
            )

        if not chapters:
            raise FileValidationError("EPUB has no readable chapter content")
        return chapters
