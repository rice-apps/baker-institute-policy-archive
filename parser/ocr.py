from dataclasses import dataclass


class Document:
    def __init__(self, doc_id: str, doc_type: str, content: bytes):
        self.id = doc_id
        self.type = doc_type
        self.content = content

    def get_type(self) -> str:
        return self.type

    def get_content(self) -> bytes:
        return self.content


@dataclass
class ParseResult:
    doc_id: str
    text: str
    # confidence: float
    # pages: list[PageResult]


class Parser:
    VALID_DOC_TYPES = {"PDF", "TIF"}

    def parse(self, docs: list[Document]) -> list[ParseResult]:
        invalid = [d for d in docs if d.get_type().upper() not in self.VALID_DOC_TYPES]
        if invalid:
            raise ValueError(
                f"Unsupported type(s): {[d.get_type() for d in invalid]}. "
                f"Allowed: {sorted(self.VALID_DOC_TYPES)}"
            )
        return [self._parse_one(doc) for doc in docs]

    def _parse_one(self, doc: Document) -> ParseResult:
        raise NotImplementedError
