"""Compare parser output with human-verified reference documents."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Iterable

from .models import ParseResult


@dataclass(frozen=True)
class ReferencePage:
    page_number: int
    text: str


@dataclass(frozen=True)
class ReferenceDocument:
    """Known-good text and review context for one source document.

    ``critical_terms`` should contain names, dates, identifiers, or phrases
    whose loss would change how a researcher interprets the document.
    """

    doc_id: str
    pages: list[ReferencePage]
    context: str = ""
    critical_terms: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n\n".join(page.text for page in self.pages)


@dataclass(frozen=True)
class EvaluationThresholds:
    """Optional project-specific acceptance limits; rates and recalls are 0–1."""

    max_character_error_rate: float | None = None
    max_word_error_rate: float | None = None
    min_token_overlap_score: float | None = None
    min_page_coverage: float | None = None
    min_critical_term_recall: float | None = None
    min_semantic_score: float | None = None

    def __post_init__(self):
        for name, value in vars(self).items():
            if value is not None and (not math.isfinite(value) or not 0 <= value <= 1):
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True)
class PageEvaluation:
    page_number: int
    character_error_rate: float | None
    word_error_rate: float | None
    token_overlap_score: float | None
    missing_from_parse: bool = False
    unexpected_in_parse: bool = False


@dataclass(frozen=True)
class DocumentEvaluation:
    doc_id: str
    character_error_rate: float
    word_error_rate: float
    word_similarity: float
    token_overlap_score: float
    page_coverage: float | None
    critical_term_recall: float | None
    missing_critical_terms: list[str]
    semantic_score: float | None
    page_results: list[PageEvaluation]
    passed_thresholds: bool | None
    unevaluable_thresholds: list[str]


@dataclass(frozen=True)
class CorpusEvaluation:
    document_coverage: float
    average_character_error_rate: float | None
    average_word_error_rate: float | None
    average_token_overlap_score: float | None
    document_results: list[DocumentEvaluation]
    missing_document_ids: list[str]
    unexpected_document_ids: list[str]


# A caller can plug in a domain-specific model or human scorer. It receives the
# supplied context, reference text, and parsed text; its score must be in [0, 1].
SemanticScorer = Callable[[ReferenceDocument, str], float]


def evaluate_corpus(
    references: Iterable[ReferenceDocument],
    parsed_results: Iterable[ParseResult],
    *,
    thresholds: EvaluationThresholds | None = None,
    semantic_scorer: SemanticScorer | None = None,
) -> CorpusEvaluation:
    """Match parser results to references by ID and score the whole sample set."""
    reference_list = list(references)
    parsed_list = list(parsed_results)
    reference_by_id = _index_unique(reference_list, "reference")
    parsed_by_id = _index_unique(parsed_list, "parsed")

    matched_ids = [doc.doc_id for doc in reference_list if doc.doc_id in parsed_by_id]
    results = [
        evaluate_document(
            reference_by_id[doc_id],
            parsed_by_id[doc_id],
            thresholds=thresholds,
            semantic_scorer=semantic_scorer,
        )
        for doc_id in matched_ids
    ]
    missing_ids = [doc.doc_id for doc in reference_list if doc.doc_id not in parsed_by_id]
    unexpected_ids = [doc.doc_id for doc in parsed_list if doc.doc_id not in reference_by_id]
    document_coverage = len(matched_ids) / len(reference_list) if reference_list else 0.0

    return CorpusEvaluation(
        document_coverage=document_coverage,
        average_character_error_rate=_mean(result.character_error_rate for result in results),
        average_word_error_rate=_mean(result.word_error_rate for result in results),
        average_token_overlap_score=_mean(result.token_overlap_score for result in results),
        document_results=results,
        missing_document_ids=missing_ids,
        unexpected_document_ids=unexpected_ids,
    )


def evaluate_document(
    reference: ReferenceDocument,
    parsed: ParseResult,
    *,
    thresholds: EvaluationThresholds | None = None,
    semantic_scorer: SemanticScorer | None = None,
) -> DocumentEvaluation:
    """Produce an OCR scorecard against verified text and optional context.

    Character and word error rates are deterministic. An optional scorer can
    judge meaning using ``reference.context`` and ``reference.critical_terms``;
    no semantic score is implied when no scorer is configured.
    """
    if reference.doc_id != parsed.doc_id:
        raise ValueError(
            f"Document IDs do not match: reference={reference.doc_id!r}, "
            f"parsed={parsed.doc_id!r}"
        )

    reference_text = reference.text
    parsed_text = parsed.text
    character_error_rate = _error_rate(
        _normalize(reference_text), _normalize(parsed_text), list
    )
    word_error_rate = _error_rate(
        _tokens(reference_text), _tokens(parsed_text), lambda value: value
    )
    token_overlap_score = _multiset_jaccard(_tokens(reference_text), _tokens(parsed_text))

    normalized_parsed_tokens = _tokens(parsed_text)
    missing_terms = [
        term
        for term in reference.critical_terms
        if not _contains_phrase(normalized_parsed_tokens, _tokens(term))
    ]
    critical_term_recall = (
        (len(reference.critical_terms) - len(missing_terms)) / len(reference.critical_terms)
        if reference.critical_terms
        else None
    )

    page_results, page_coverage = _evaluate_pages(reference.pages, parsed.pages)
    semantic_score = None
    if semantic_scorer is not None:
        semantic_score = semantic_scorer(reference, parsed_text)
        if not math.isfinite(semantic_score) or not 0 <= semantic_score <= 1:
            raise ValueError("semantic_scorer must return a finite score between 0 and 1")

    passed, unevaluable = _check_thresholds(
        thresholds,
        character_error_rate=character_error_rate,
        word_error_rate=word_error_rate,
        token_overlap_score=token_overlap_score,
        page_coverage=page_coverage,
        critical_term_recall=critical_term_recall,
        semantic_score=semantic_score,
    )
    return DocumentEvaluation(
        doc_id=reference.doc_id,
        character_error_rate=character_error_rate,
        word_error_rate=word_error_rate,
        word_similarity=max(0.0, 1.0 - word_error_rate),
        token_overlap_score=token_overlap_score,
        page_coverage=page_coverage,
        critical_term_recall=critical_term_recall,
        missing_critical_terms=missing_terms,
        semantic_score=semantic_score,
        page_results=page_results,
        passed_thresholds=passed,
        unevaluable_thresholds=unevaluable,
    )


def _index_unique(documents, kind: str):
    indexed = {}
    for document in documents:
        if document.doc_id in indexed:
            raise ValueError(f"Duplicate {kind} document ID: {document.doc_id!r}")
        indexed[document.doc_id] = document
    return indexed


def _mean(values):
    values = list(values)
    return sum(values) / len(values) if values else None


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(normalized.split())


def _tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return re.findall(r"\w+(?:['’]\w+)*", normalized)


def _contains_phrase(tokens: list[str], phrase: list[str]) -> bool:
    if not phrase:
        return True
    width = len(phrase)
    return any(tokens[start : start + width] == phrase for start in range(len(tokens) - width + 1))


def _multiset_jaccard(reference: list[str], parsed: list[str]) -> float:
    """Token intersection over union, counting repeated words by frequency."""
    reference_counts = Counter(reference)
    parsed_counts = Counter(parsed)
    union_count = sum((reference_counts | parsed_counts).values())
    if union_count == 0:
        return 1.0
    intersection_count = sum((reference_counts & parsed_counts).values())
    return intersection_count / union_count


def _edit_distance(reference: list[str] | str, parsed: list[str] | str) -> int:
    """Levenshtein distance with memory proportional to the shorter input."""
    if len(reference) < len(parsed):
        reference, parsed = parsed, reference
    previous = list(range(len(parsed) + 1))
    for ref_index, ref_unit in enumerate(reference, start=1):
        current = [ref_index]
        for parsed_index, parsed_unit in enumerate(parsed, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[parsed_index] + 1,
                    previous[parsed_index - 1] + (ref_unit != parsed_unit),
                )
            )
        previous = current
    return previous[-1]


def _error_rate(reference: list[str] | str, parsed: list[str] | str, units: Callable):
    reference_units = units(reference)
    parsed_units = units(parsed)
    if not reference_units:
        return 0.0 if not parsed_units else 1.0
    return _edit_distance(reference_units, parsed_units) / len(reference_units)


def _evaluate_pages(reference_pages: list[ReferencePage], parsed_pages: list[str]):
    if not parsed_pages:
        return [], None
    if not reference_pages:
        return [
            PageEvaluation(
                page_number=index,
                character_error_rate=None,
                word_error_rate=None,
                token_overlap_score=None,
                unexpected_in_parse=True,
            )
            for index in range(1, len(parsed_pages) + 1)
        ], None

    results = []
    for index in range(max(len(reference_pages), len(parsed_pages))):
        has_reference = index < len(reference_pages)
        has_parse = index < len(parsed_pages)
        if has_reference and has_parse:
            reference_page = reference_pages[index]
            parsed_page = parsed_pages[index]
            results.append(
                PageEvaluation(
                    page_number=reference_page.page_number,
                    character_error_rate=_error_rate(
                        _normalize(reference_page.text), _normalize(parsed_page), list
                    ),
                    word_error_rate=_error_rate(
                        _tokens(reference_page.text), _tokens(parsed_page), lambda value: value
                    ),
                    token_overlap_score=_multiset_jaccard(
                        _tokens(reference_page.text), _tokens(parsed_page)
                    ),
                )
            )
        elif has_reference:
            results.append(
                PageEvaluation(
                    page_number=reference_pages[index].page_number,
                    character_error_rate=1.0 if _normalize(reference_pages[index].text) else 0.0,
                    word_error_rate=1.0 if _tokens(reference_pages[index].text) else 0.0,
                    token_overlap_score=None,
                    missing_from_parse=True,
                )
            )
        else:
            results.append(
                PageEvaluation(
                    page_number=index + 1,
                    character_error_rate=None,
                    word_error_rate=None,
                    token_overlap_score=None,
                    unexpected_in_parse=True,
                )
            )
    return results, min(len(parsed_pages) / len(reference_pages), 1.0)


def _check_thresholds(
    thresholds: EvaluationThresholds | None,
    *,
    character_error_rate: float,
    word_error_rate: float,
    token_overlap_score: float,
    page_coverage: float | None,
    critical_term_recall: float | None,
    semantic_score: float | None,
):
    if thresholds is None:
        return None, []

    configured = {
        "character_error_rate": (thresholds.max_character_error_rate, character_error_rate, "max"),
        "word_error_rate": (thresholds.max_word_error_rate, word_error_rate, "max"),
        "token_overlap_score": (thresholds.min_token_overlap_score, token_overlap_score, "min"),
        "page_coverage": (thresholds.min_page_coverage, page_coverage, "min"),
        "critical_term_recall": (
            thresholds.min_critical_term_recall,
            critical_term_recall,
            "min",
        ),
        "semantic_score": (thresholds.min_semantic_score, semantic_score, "min"),
    }
    checks = []
    unevaluable = []
    for name, (limit, value, direction) in configured.items():
        if limit is None:
            continue
        if value is None:
            unevaluable.append(name)
        elif direction == "max":
            checks.append(value <= limit)
        else:
            checks.append(value >= limit)
    if not checks and not unevaluable:
        return None, []
    if any(not check for check in checks):
        return False, unevaluable
    if unevaluable:
        return None, unevaluable
    return True, []
