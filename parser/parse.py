from models import Document, DocumentType, ParseResult


class Parser:
    VALID_DOC_TYPES = set(DocumentType)

    def parse(self, docs: list[Document]) -> list[ParseResult]:
        invalid = [doc for doc in docs if doc.get_type() not in self.VALID_DOC_TYPES]
        if invalid:
            raise ValueError(
                f"Unsupported type(s): {[doc.get_type() for doc in invalid]}. "
                f"Allowed: {sorted(doc_type.value for doc_type in self.VALID_DOC_TYPES)}"
            )
        return [self._parse_one(doc) for doc in docs]

    def _parse_one(self, doc: Document) -> ParseResult:
        raise NotImplementedError
