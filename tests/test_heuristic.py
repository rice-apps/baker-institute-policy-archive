import json
from pathlib import Path

import pytest

from itemization import HeuristicConfig, HeuristicItemizer, Page
from itemization.grouping import build_items
from itemization.models import Boundary

FIXTURE = Path(__file__).parent / "fixtures" / "pcast_example.json"


def load_pcast() -> list[Page]:
    return [Page(**p) for p in json.loads(FIXTURE.read_text(encoding="utf-8"))]


def ranges(result):
    return [[(r.document_id, r.start_page, r.end_page) for r in it.page_ranges] for it in result.items]


def P(doc, n, *lines):
    return Page(doc, n, list(lines))


# ---------- real sample: PCAST swearing-in packet ----------


def test_pcast_expected_items():
    result = HeuristicItemizer().itemize(load_pcast())
    assert ranges(result) == [
        [("example", 1, 2)],
        [("example", 3, 3)],
        [("example", 4, 4)],
        [("example", 5, 6)],
    ]


def test_pcast_boundary_scores_and_reasons():
    result = HeuristicItemizer().itemize(load_pcast())
    assert len(result.boundaries) == 5
    splits = [b.starts_new_item for b in result.boundaries]
    assert splits == [False, True, True, True, False]
    for item in result.items[1:]:
        assert item.reason
        assert item.confidence is not None
    assert any("section_numeral_sequence" in s for s in result.boundaries[0].signals)


def test_pcast_short_version_matches_full():
    full = load_pcast()
    short = [Page(p.document_id, p.page_number, p.lines()[:5] + p.lines()[-5:]) for p in full]
    assert ranges(HeuristicItemizer().itemize(short)) == ranges(HeuristicItemizer().itemize(full))


# ---------- small made-up cases ----------


def test_empty_and_single_page():
    it = HeuristicItemizer()
    assert it.itemize([]).items == []
    one = it.itemize([P("a", 1, "Hello")])
    assert ranges(one) == [[("a", 1, 1)]]
    assert one.boundaries == []


def test_string_text_is_accepted():
    pages = [Page("a", 1, "MEMORANDUM\nTO: X\nbody"), Page("a", 2, "continued text here")]
    assert len(HeuristicItemizer().itemize(pages).items) == 1


def test_memo_header_starts_new_item():
    pages = [
        P("a", 1, "Some body text", "more body text", "Sincerely,", "J. Smith"),
        P("a", 2, "MEMORANDUM", "TO: Director", "FROM: Staff", "SUBJECT: Budget", "body"),
    ]
    assert ranges(HeuristicItemizer().itemize(pages)) == [[("a", 1, 1)], [("a", 2, 2)]]


def test_continued_marker_keeps_one_item():
    pages = [P("a", 1, "body text", "(continued)"), P("a", 2, "MEMORANDUM", "more text")]
    assert len(HeuristicItemizer().itemize(pages).items) == 1


def test_page_k_of_n_keeps_one_item():
    pages = [
        P("a", 1, "THE REPORT", "FINAL DRAFT", "text", "Page 1 of 3"),
        P("a", 2, "Page 2 of 3", "more text", "even more"),
    ]
    assert len(HeuristicItemizer().itemize(pages).items) == 1


def test_printed_page_numbers_keep_one_item():
    pages = [P("a", 1, "text", "3"), P("a", 2, "4", "text")]
    assert len(HeuristicItemizer().itemize(pages).items) == 1


def test_document_change_splits_by_default():
    pages = [P("a", 1, "body text"), P("b", 1, "body text")]
    assert ranges(HeuristicItemizer().itemize(pages)) == [[("a", 1, 1)], [("b", 1, 1)]]


def test_item_can_span_two_documents():
    pages = [P("a", 1, "body text", "(continued)"), P("b", 1, "rest of the text")]
    assert ranges(HeuristicItemizer().itemize(pages)) == [[("a", 1, 1), ("b", 1, 1)]]


def test_threshold_is_configurable():
    pages = [P("a", 1, "body text"), P("a", 2, "SENIOR STAFF", "LIST", "text")]
    assert len(HeuristicItemizer().itemize(pages).items) == 2
    strict = HeuristicItemizer(HeuristicConfig(threshold=0.9))
    assert len(strict.itemize(pages).items) == 1


def test_non_consecutive_pages_start_new_range():
    pages = [P("a", 1, "text"), P("a", 3, "text")]
    result = HeuristicItemizer(HeuristicConfig(threshold=5.0)).itemize(pages)
    assert ranges(result) == [[("a", 1, 1), ("a", 3, 3)]]


def test_build_items_checks_boundary_count():
    with pytest.raises(ValueError):
        build_items([P("a", 1, "x"), P("a", 2, "y")], [])


def test_build_items_works_with_llm_style_boundaries():
    pages = [P("a", 1, "x"), P("a", 2, "y"), P("a", 3, "z")]
    bounds = [
        Boundary(0, False, confidence=0.9, reason="same letter"),
        Boundary(1, True, confidence=0.7, reason="new memo header"),
    ]
    items = build_items(pages, bounds, method="llm")
    assert [(i.page_ranges[0].start_page, i.page_ranges[0].end_page) for i in items] == [(1, 2), (3, 3)]
    assert items[1].reason == "new memo header" and items[1].confidence == 0.7