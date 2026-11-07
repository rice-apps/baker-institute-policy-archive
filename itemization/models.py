# Basic idea: Define shared page and result dataclasses, including boundary
# scores and reasons, so all itemizers use the same input and output format.
# This is a starting point; nothing is set in stone.

from dataclasses import dataclass, field


@dataclass
class Page:
    document_id: str
    page_number: int
    text: str | list[str]  # one string, or a list of lines

    def lines(self) -> list[str]:
        raw = self.text.splitlines() if isinstance(self.text, str) else self.text
        return [ln.strip() for ln in raw if ln and ln.strip()]


@dataclass
class PageRange:
    document_id: str
    start_page: int
    end_page: int  # inclusive


@dataclass
class Boundary:
    """Decision about the gap between pages[index] and pages[index + 1]."""

    index: int
    starts_new_item: bool
    score: float | None = None
    confidence: float | None = None
    signals: list[str] = field(default_factory=list)
    reason: str | None = None


@dataclass
class ItemProposal:
    item_id: str
    page_ranges: list[PageRange]
    item_type: str | None = None
    confidence: float | None = None
    reason: str | None = None


@dataclass
class ItemizationResult:
    method: str
    items: list[ItemProposal]
    boundaries: list[Boundary] = field(default_factory=list)