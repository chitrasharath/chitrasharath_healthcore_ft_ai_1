"""PDF → markdown via markitdown."""

from __future__ import annotations

from pathlib import Path


def pdf_to_markdown(pdf_path: str) -> str:
    from markitdown import MarkItDown

    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    md = MarkItDown()
    result = md.convert(str(path))
    text = (getattr(result, "text_content", None) or str(result) or "").strip()
    if not text:
        raise ValueError("markitdown produced empty markdown")
    return text
