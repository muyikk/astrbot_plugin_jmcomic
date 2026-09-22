from __future__ import annotations

import contextlib
import io
import os
from collections.abc import Iterable
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter

from .helpers import natural_path_key

IMAGE_EXTENSIONS = {".webp", ".jpg", ".jpeg", ".png"}


def list_image_paths(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    paths = [
        path
        for path in folder.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return sorted(paths, key=natural_path_key)


def build_pdf(
    image_paths: Iterable[Path],
    output_path: Path,
    *,
    password: str | None = None,
    jpeg_quality: int | None = None,
) -> int:
    """Build a PDF atomically while decoding at most one image at a time."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    with contextlib.suppress(FileNotFoundError):
        temporary_path.unlink()

    writer = PdfWriter()
    page_count = 0
    try:
        for image_path in image_paths:
            with Image.open(image_path) as image:
                buffer = io.BytesIO()
                rgb = image.convert("RGB")
                save_options: dict[str, object] = {"format": "PDF"}
                if jpeg_quality is not None:
                    save_options.update(quality=jpeg_quality, optimize=True)
                rgb.save(buffer, **save_options)
                buffer.seek(0)
                for page in PdfReader(buffer).pages:
                    writer.add_page(page)
                    writer.pages[-1].compress_content_streams()
                    page_count += 1

        if page_count == 0:
            raise FileNotFoundError("下载目录中没有可用于生成 PDF 的图片")
        if password:
            writer.encrypt(password)
        with temporary_path.open("wb") as file:
            writer.write(file)
        os.replace(temporary_path, output_path)
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            temporary_path.unlink()
        raise
    return page_count


def cache_is_valid(
    pdf_path: Path,
    *,
    password: str | None,
    expected_pages: int,
) -> bool:
    if not pdf_path.exists():
        return False
    try:
        reader = PdfReader(str(pdf_path))
        if password is None and reader.is_encrypted:
            return False
        if password is not None:
            if not reader.is_encrypted or not reader.decrypt(password):
                return False
        return len(reader.pages) == expected_pages
    except Exception:
        return False
