import re
from dataclasses import dataclass, field
from typing import Callable, Sequence

from .base import Itemizer
from .grouping import build_items
from .models import Boundary, ItemizationResult, Page

DEFAULT_WEIGHTS: dict[str, float] = {
    # points toward "new document starts on the next page"
    "document_id_differs": 0.6,
    "date_at_top": 0.5,
    "memo_header_at_top": 0.6,
    "letter_salutation_at_top": 0.5,
    "title_block_at_top": 0.5,  # 2+ ALL-CAPS lines at the top
    "title_line_at_top": 0.3,  # exactly one ALL-CAPS line at the top
    "signature_at_bottom": 0.4,
    # points toward "same document continues"
    "continued_marker": -1.0,
    "page_k_of_n": -1.0,
    "printed_page_sequence": -0.8,
    "section_numeral_sequence": -0.6,
}

_MONTHS = (
    "january|february|march|april|may|june|july|august|september|october|"
    "november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
)
_DATE_RE = re.compile(
    rf"\b(?:{_MONTHS})\.?\s+\d{{1,2}},?\s+\d{{4}}\b|\b\d{{1,2}}/\d{{1,2}}/\d{{2,4}}\b",
    re.IGNORECASE,
)
_MEMO_RE = re.compile(r"^(memorandum|memo)\b|^(to|from|subject|re)\s*:", re.IGNORECASE)
_SALUTATION_RE = re.compile(r"^dear\b", re.IGNORECASE)
_SIGNOFF_RE = re.compile(
    r"^(sincerely|respectfully|very truly yours|cordially|best regards|prepared by)\b",
    re.IGNORECASE,
)
_TITLE_LINE_RE = re.compile(
    r"^(director|chairman|chair|secretary|deputy director|assistant to the president)\b",
    re.IGNORECASE,
)
_CONTINUED_RE = re.compile(r"\(?\bcont(?:inued|'d)\b", re.IGNORECASE)
_PAGE_K_OF_N_RE = re.compile(r"\bpage\s+(\d+)\s+of\s+(\d+)\b", re.IGNORECASE)
_BARE_NUMBER_RE = re.compile(r"^[-–—\s]*(\d{1,4})[-–—\s]*$")
_ROMAN_HEADING_RE = re.compile(r"^([IVX]+)\.\s")
_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10}


def _roman(s: str) -> int:
    total = 0
    for i, ch in enumerate(s):
        v = _ROMAN_VALUES[ch]
        total += -v if i + 1 < len(s) and _ROMAN_VALUES[s[i + 1]] > v else v
    return total


def _is_caps(line: str) -> bool:
    letters = [c for c in line if c.isalpha()]
    return len(letters) >= 3 and all(c.isupper() for c in letters)


@dataclass
class HeuristicConfig:
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    threshold: float = 0.5  # split when the total reaches this
    top_n: int = 5
    bottom_n: int = 5


class HeuristicItemizer(Itemizer):
    def __init__(self, config: HeuristicConfig | None = None):
        self.config = config or HeuristicConfig()

    def _signals(self) -> list[tuple[str, Callable[[Page, Page], bool]]]:
        n_top, n_bot = self.config.top_n, self.config.bottom_n

        def top(p: Page) -> list[str]:
            return p.lines()[:n_top]

        def bottom(p: Page) -> list[str]:
            return p.lines()[-n_bot:]

        def doc_differs(cur: Page, nxt: Page) -> bool:
            return cur.document_id != nxt.document_id

        def date_at_top(cur: Page, nxt: Page) -> bool:
            return any(_DATE_RE.search(ln) for ln in top(nxt))

        def memo_header(cur: Page, nxt: Page) -> bool:
            return any(_MEMO_RE.search(ln) for ln in top(nxt))

        def salutation(cur: Page, nxt: Page) -> bool:
            return any(_SALUTATION_RE.search(ln) for ln in top(nxt))

        def caps_run(nxt: Page) -> int:
            n = 0
            for ln in top(nxt):
                if not _is_caps(ln):
                    break
                n += 1
            return n

        def title_block(cur: Page, nxt: Page) -> bool:
            return caps_run(nxt) >= 2

        def title_line(cur: Page, nxt: Page) -> bool:
            return caps_run(nxt) == 1

        def signature(cur: Page, nxt: Page) -> bool:
            lines = bottom(cur)
            if any(_SIGNOFF_RE.search(ln) for ln in lines):
                return True
            return any(_TITLE_LINE_RE.search(ln) for ln in lines[-3:])

        def continued(cur: Page, nxt: Page) -> bool:
            return any(_CONTINUED_RE.search(ln) for ln in bottom(cur) + top(nxt))

        def page_k_of_n(cur: Page, nxt: Page) -> bool:
            def find(lines: list[str]) -> tuple[int, int] | None:
                for ln in lines:
                    m = _PAGE_K_OF_N_RE.search(ln)
                    if m:
                        return int(m.group(1)), int(m.group(2))
                return None

            a = find(bottom(cur) + top(cur))
            b = find(top(nxt) + bottom(nxt))
            return bool(a and b and a[1] == b[1] and b[0] == a[0] + 1)

        def printed_page_sequence(cur: Page, nxt: Page) -> bool:
            def number(p: Page) -> int | None:
                lines = p.lines()
                for ln in lines[-1:] + lines[:1]:
                    m = _BARE_NUMBER_RE.match(ln)
                    if m:
                        return int(m.group(1))
                return None

            a, b = number(cur), number(nxt)
            return a is not None and b is not None and b == a + 1

        def numeral_sequence(cur: Page, nxt: Page) -> bool:
            first = top(nxt)[:1]
            m_next = _ROMAN_HEADING_RE.match(first[0]) if first else None
            if not m_next:
                return False
            prev = None
            for ln in cur.lines():
                m = _ROMAN_HEADING_RE.match(ln)
                if m:
                    prev = m.group(1)
            return prev is not None and _roman(m_next.group(1)) == _roman(prev) + 1

        return [
            ("document_id_differs", doc_differs),
            ("date_at_top", date_at_top),
            ("memo_header_at_top", memo_header),
            ("letter_salutation_at_top", salutation),
            ("title_block_at_top", title_block),
            ("title_line_at_top", title_line),
            ("signature_at_bottom", signature),
            ("continued_marker", continued),
            ("page_k_of_n", page_k_of_n),
            ("printed_page_sequence", printed_page_sequence),
            ("section_numeral_sequence", numeral_sequence),
        ]

    def score_boundary(self, cur: Page, nxt: Page) -> tuple[float, list[str]]:
        score, fired = 0.0, []
        for name, check in self._signals():
            weight = self.config.weights.get(name, 0.0)
            if weight and check(cur, nxt):
                score += weight
                fired.append(f"{name}({weight:+.1f})")
        return score, fired

    def itemize(self, pages: Sequence[Page]) -> ItemizationResult:
        threshold = self.config.threshold
        boundaries: list[Boundary] = []
        for i in range(len(pages) - 1):
            score, fired = self.score_boundary(pages[i], pages[i + 1])
            split = score >= threshold
            confidence = min(1.0, 0.5 + abs(score - threshold) / (2 * max(threshold, 1e-9)))
            boundaries.append(
                Boundary(
                    index=i,
                    starts_new_item=split,
                    score=round(score, 3),
                    confidence=round(confidence, 3),
                    signals=fired,
                )
            )
        items = build_items(pages, boundaries, method="heuristic")
        return ItemizationResult(method="heuristic", items=items, boundaries=boundaries)