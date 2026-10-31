# Basic idea: Define shared page and result dataclasses, including boundary
# scores and reasons, so all itemizers use the same input and output format.
# This is a starting point; nothing is set in stone.

from __future__ import annotations

from dataclasses import dataclass

@dataclass
class Page:
    document_id: str
    page_number: int
    text: list[str]


@dataclass
class PageRange:
    document_id: str
    start_page: int
    end_page: int


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
