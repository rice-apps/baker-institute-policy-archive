# Comparing parser output with reference documents

The evaluation module compares parser output with a human-verified reference for the same document. It reports:

- Character error rate (CER), after Unicode normalization, case folding, and whitespace normalization.
- Word error rate (WER), using word tokens and ignoring punctuation.
- Word-token overlap score using intersection over union (multiset Jaccard), so repeated words count.
- Per-page CER and WER, plus missing or unexpected parsed pages when page boundaries are available.
- Recall of reviewer-selected critical names, dates, identifiers, or phrases.
- An optional semantic score from a caller-provided scorer that receives the reference context.

The main overlap score is `sum(min(reference_count, parsed_count)) / sum(max(reference_count, parsed_count))` across normalized word tokens. It ranges from 0 to 1; a perfect match is 1. It follows the union/intersection idea while counting repeated words. It ignores word order, so CER and WER remain useful companion measures. Critical-term recall highlights errors that can alter meaning even when the overall text score is strong. A semantic score is only included when a project supplies a scorer; context by itself is not treated as a score.

```python
from parser.evaluation import (
    EvaluationThresholds,
    ReferenceDocument,
    ReferencePage,
    evaluate_corpus,
)
from parser.models import ParseResult

reference = ReferenceDocument(
    doc_id="memo-17.pdf",
    pages=[
        ReferencePage(1, "To: Secretary of Energy\nDate: March 4, 1993\nSubject: Nuclear policy review"),
        ReferencePage(2, "The committee recommends a six-month review."),
    ],
    context="A policy memo about the 1993 nuclear policy review.",
    critical_terms=["Secretary of Energy", "March 4, 1993", "six-month review"],
)
parsed = ParseResult(
    doc_id="memo-17.pdf",
    text="To: Secretary of Energy\nDate: March 4, 1993\nSubject: Nuclear policy review\n\nThe committee recommends a six-month review.",
    pages=[
        "To: Secretary of Energy\nDate: March 4, 1993\nSubject: Nuclear policy review",
        "The committee recommends a six-month review.",
    ],
)

report = evaluate_corpus(
    [reference],
    [parsed],
    thresholds=EvaluationThresholds(
        max_word_error_rate=0.03,
        min_token_overlap_score=0.90,
        min_page_coverage=1.0,
        min_critical_term_recall=1.0,
    ),
    # Optional: semantic_scorer=lambda reference, parsed_text: ...
)
print(report)
```

Run the sample from the repository root. Use `evaluate_document` for a single file or `evaluate_corpus` for a sample set. The corpus report matches by `doc_id`, lists missing and unexpected documents, and gives macro-average CER/WER/token-overlap score across matched documents. Each matched document includes its own page and critical-term detail.

`ReferenceDocument.context` is supplied to the optional semantic scorer so it can use document-specific meaning. Keep a versioned, representative reference set for each parser you want to compare. Thresholds should be chosen against reviewed examples; they are not universal quality cutoffs.
