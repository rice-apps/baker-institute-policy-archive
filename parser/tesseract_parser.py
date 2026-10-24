import io

import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageSequence

from parse import Document, ParseResult, Parser


class TesseractParser(Parser):
    def __init__(self, dpi: int = 300, lang: str = "eng", tesseract_cmd: str | None = None):
        self.dpi = dpi
        self.lang = lang
        if tesseract_cmd:  # only needed if tesseract isn't on PATH (common on Windows)
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def _parse_one(self, doc: Document) -> ParseResult:
        doc_type = doc.get_type().upper()
        if doc_type == "PDF":
            images = self._pdf_to_images(doc.get_content())
        elif doc_type == "TIF":
            images = self._tif_to_images(doc.get_content())
        else:
            raise ValueError(f"Unsupported type: {doc.get_type()}")

        pages = [pytesseract.image_to_string(img, lang=self.lang) for img in images]
        return ParseResult(doc_id=doc.id, text="\n\n".join(pages).strip())

    def _pdf_to_images(self, content: bytes):
        with fitz.open(stream=content, filetype="pdf") as pdf:
            for page in pdf:
                pix = page.get_pixmap(dpi=self.dpi, alpha=False)
                yield Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    def _tif_to_images(self, content: bytes):
        with Image.open(io.BytesIO(content)) as img:
            for frame in ImageSequence.Iterator(img):  # multi-page TIFFs
                yield frame.convert("RGB")