from models import Document, DocumentType, Page


class Parser:
    VALID_DOC_TYPES = set(DocumentType)

    def parse(self, docs: list[Document]) -> list[Page]:
        invalid = [doc for doc in docs if doc.get_type() not in self.VALID_DOC_TYPES]
        if invalid:
            raise ValueError(
                f"Unsupported type(s): {[doc.get_type() for doc in invalid]}. "
                f"Allowed: {sorted(doc_type.value for doc_type in self.VALID_DOC_TYPES)}"
            )
        return [page for doc in docs for page in self._parse_one(doc)]

    def _parse_one(self, doc: Document) -> list[Page]:
        raise NotImplementedError
