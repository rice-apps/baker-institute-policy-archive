from pathlib import Path

from load_files import load_files
from tesseract_parser import TesseractParser


def main():
    docs = load_files("test_files")
    print(f"Loaded {len(docs)} documents")

    results = TesseractParser(dpi=300).parse(docs)

    out_dir = Path("ocr_output")
    out_dir.mkdir(exist_ok=True)
    for r in results:
        (out_dir / f"{Path(r.doc_id).stem}.txt").write_text(r.text, encoding="utf-8")
        print(f"{r.doc_id}: {len(r.text)} characters")


if __name__ == "__main__":
    main()
    