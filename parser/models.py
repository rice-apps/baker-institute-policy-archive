from dataclasses import dataclass, field
from enum import Enum


class DocumentType(str, Enum):
    PDF = "PDF"
    TIF = "TIF"


class Document:
    def __init__(self, doc_id: str, doc_type: DocumentType, content: bytes):
        self.id = doc_id
        self.type = DocumentType(doc_type.upper())
        self.content = content

    def get_type(self) -> DocumentType:
        return self.type

    def get_content(self) -> bytes:
        return self.content


@dataclass
class ParseResult:
    doc_id: str
    text: str
    pages: list[str] = field(default_factory=list)
    # confidence: float
