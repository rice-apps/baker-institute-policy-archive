import json
from dataclasses import asdict
from pathlib import Path

from load_files import load_files
from tesseract_parser import TesseractParser


def main():
    docs = load_files("test_files")
    print(f"Loaded {len(docs)} documents")

    results = TesseractParser(dpi=300).parse(docs)

    out_dir = Path("ocr_output")
    out_dir.mkdir(exist_ok=True)
    pages_by_document = {}
    for page in results:
        pages_by_document.setdefault(page.document_id, []).append(page)

    for document_id, pages in pages_by_document.items():
        output_path = out_dir / f"{document_id}.json"
        output_path.write_text(
            json.dumps([asdict(page) for page in pages], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {len(pages)} page results to {output_path}")


if __name__ == "__main__":
    main()
