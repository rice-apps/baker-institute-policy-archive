"""Document parsing and quality evaluation interfaces."""

from .evaluation import (
    CorpusEvaluation,
    DocumentEvaluation,
    EvaluationThresholds,
    ReferenceDocument,
    ReferencePage,
    evaluate_corpus,
    evaluate_document,
)
from .models import Document, DocumentType, ParseResult

__all__ = [
    "CorpusEvaluation",
    "Document",
    "DocumentEvaluation",
    "DocumentType",
    "EvaluationThresholds",
    "ParseResult",
    "ReferenceDocument",
    "ReferencePage",
    "evaluate_corpus",
    "evaluate_document",
]
