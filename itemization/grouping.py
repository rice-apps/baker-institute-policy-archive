from typing import Sequence

from .models import Boundary, ItemProposal, Page, PageRange


def _add_page(ranges: list[PageRange], page: Page) -> None:
    last = ranges[-1] if ranges else None
    if (
        last is not None
        and last.document_id == page.document_id
        and page.page_number == last.end_page + 1
    ):
        last.end_page = page.page_number
    else:
        ranges.append(PageRange(page.document_id, page.page_number, page.page_number))


def build_items(
    pages: Sequence[Page], boundaries: Sequence[Boundary], method: str = ""
) -> list[ItemProposal]:
    if not pages:
        return []
    if len(boundaries) != len(pages) - 1:
        raise ValueError(
            f"expected {len(pages) - 1} boundaries for {len(pages)} pages, got {len(boundaries)}"
        )

    items: list[ItemProposal] = []
    current_ranges: list[PageRange] = []
    start_boundary: Boundary | None = None

    def close() -> None:
        confidence = None
        if start_boundary is not None:
            confidence = start_boundary.confidence
            reason = ", ".join(start_boundary.signals) or start_boundary.reason
        else:
            reason = "first page"
        items.append(
            ItemProposal(
                item_id=f"{method or 'item'}-{len(items) + 1:04d}",
                page_ranges=current_ranges,
                confidence=confidence,
                reason=reason,
            )
        )

    _add_page(current_ranges, pages[0])
    for i, boundary in enumerate(boundaries):
        if boundary.starts_new_item:
            close()
            current_ranges = []
            start_boundary = boundary
        _add_page(current_ranges, pages[i + 1])
    close()
    return items