from pathlib import Path

from parse import Document

EXT_TO_TYPE = {".pdf": "PDF", ".tif": "TIF", ".tiff": "TIF"}


def load_files(directory: str = "test_files") -> list[Document]:
    """Load every supported file in `directory` as a Document.

    A relative path is resolved against this file's location, so it works
    regardless of where you launch the script from.
    """
    base = Path(__file__).resolve().parent / directory
    if not base.is_dir():
        raise FileNotFoundError(f"Directory not found: {base}")

    docs = []
    for path in sorted(base.iterdir()):
        doc_type = EXT_TO_TYPE.get(path.suffix.lower())
        if doc_type is None:
            continue  # skip unsupported files
        docs.append(Document(doc_id=path.name, doc_type=doc_type, content=path.read_bytes()))
    return docs