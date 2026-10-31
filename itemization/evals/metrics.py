"""Compare item ranges against a human-verified grouping."""


def expand_items(pages, result):
    """Expand ranges and require every input page exactly once, in order."""
    references = [(page["document_id"], page["page_number"]) for page in pages]
    if len(references) != len(set(references)):
        raise ValueError("Input contains duplicate source page references.")

    items = []
    for item in result["items"]:
        members = []
        for span in item["page_ranges"]:
            start, end = span["start_page"], span["end_page"]
            if type(start) is not int or type(end) is not int or start < 1 or end < start:
                raise ValueError("Page ranges must use positive, inclusive integer bounds.")
            members.extend((span["document_id"], number) for number in range(start, end + 1))
        if not members:
            raise ValueError("Items must contain at least one page.")
        items.append(tuple(members))

    if [page for item in items for page in item] != references:
        raise ValueError("Items must cover every input page exactly once, in input order.")
    return items


def boundaries(items):
    """Return input indices of item starts, excluding the first page."""
    starts = set()
    offset = 0
    for item in items:
        if offset:
            starts.add(offset)
        offset += len(item)
    return starts


def evaluate(pages, expected, predicted):
    expected_items = expand_items(pages, expected)
    predicted_items = expand_items(pages, predicted)
    expected_splits = boundaries(expected_items)
    predicted_splits = boundaries(predicted_items)
    correct = len(expected_splits & predicted_splits)
    # No boundaries on either side is a perfect segmentation. If only one
    # side has boundaries, an undefined precision or recall is reported as 0.
    precision = correct / len(predicted_splits) if predicted_splits else float(not expected_splits)
    recall = correct / len(expected_splits) if expected_splits else float(not predicted_splits)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    def locations(indices):
        return [
            {"before_document_id": pages[i]["document_id"], "before_page_number": pages[i]["page_number"]}
            for i in sorted(indices)
        ]

    return {
        "expected_items": len(expected_items),
        "predicted_items": len(predicted_items),
        "exact_item_matches": len(set(expected_items) & set(predicted_items)),
        "correct_splits": correct,
        "boundary_precision": precision,
        "boundary_recall": recall,
        "boundary_f1": f1,
        "extra_splits": locations(predicted_splits - expected_splits),
        "missed_splits": locations(expected_splits - predicted_splits),
    }
