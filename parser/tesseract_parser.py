import io

import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageSequence

from models import Document, DocumentType, Page
from parse import Parser


class TesseractParser(Parser):
    def __init__(self, dpi: int = 300, lang: str = "eng", tesseract_cmd: str | None = None):
        self.dpi = dpi
        self.lang = lang
        if tesseract_cmd:  # only needed if tesseract isn't on PATH (common on Windows)
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    def _parse_one(self, doc: Document) -> list[Page]:
        doc_type = doc.get_type()
        if doc_type is DocumentType.PDF:
            images = self._pdf_to_images(doc.get_content())
        elif doc_type is DocumentType.TIF:
            images = self._tif_to_images(doc.get_content())
        else:
            raise ValueError(f"Unsupported type: {doc.get_type()}")

        return [
            Page(
                document_id=doc.id,
                page_number=page_number,
                text=pytesseract.image_to_string(image, lang=self.lang).strip(),
            )
            for page_number, image in enumerate(images, start=1)
        ]

    def _pdf_to_images(self, content: bytes):
        with fitz.open(stream=content, filetype="pdf") as pdf:
            for page in pdf:
                pix = page.get_pixmap(dpi=self.dpi, alpha=False)
                yield Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    def _tif_to_images(self, content: bytes):
        with Image.open(io.BytesIO(content)) as img:
            for frame in ImageSequence.Iterator(img):  # multi-page TIFFs
                yield frame.convert("RGB")
