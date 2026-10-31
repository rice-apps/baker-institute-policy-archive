# Itemization Evals

Compare itemizers against human-verified document boundaries to measure accuracy, catch regressions, and identify errors requiring review.

## Test Cases

Use sequential case IDs (`case_001`, `case_002`, etc.). Store each pair in `cases/`:

- `cases/<case>_pages.json`: Ordered OCR pages with `document_id`, one-based `page_number`, and full `text` as a list of lines.
- `cases/<case>_expected.json`: Correct items represented by inclusive page ranges, verified using the client itemization guidelines.

Expected output format:

```json
{
  "items": [
    {
      "page_ranges": [
        {"document_id": "sample", "start_page": 1, "end_page": 2}
      ]
    },
    {
      "page_ranges": [
        {"document_id": "sample", "start_page": 3, "end_page": 3}
      ]
    }
  ]
}
```

An item may span multiple PDFs. Every input page must appear exactly once, in order. Expected results do not require generated IDs, confidence scores, or explanations.

`case_001_pages.json` pairs with `case_001_expected.json`: the ceremony briefing (pages 1–2), staff list (3), appointees (4), and talking points (5–6). This grouping is human-confirmed, with attachments treated as separate items. Case IDs identify fixtures; `document_id` continues to identify the source PDF.

## Evaluation

From the repository root, run an implemented itemizer:

```bash
python3 -m itemization.evals.run --method heuristic --case case_001
python3 -m itemization.evals.run --method llm --case case_001
```

The runner loads OCR pages as `Page` objects, calls `itemize(pages)`, and scores the returned `ItemizationResult`. Add `HeuristicItemizer` in `itemization/heuristic.py` or `LLMItemizer` in `itemization/llm.py`. Each must support construction without arguments (or have a factory configured in `run_itemizer`). These implementations do not exist yet. LLM runs may call a paid API.

Alternatively, evaluate saved output JSON with the same `items` / `page_ranges` structure:

```bash
python3 -m itemization.evals.run --case case_001 --predictions /path/to/predictions.json
```

The runner evaluates one case and prints a JSON report. Invalid page coverage fails evaluation. Extra fields such as method, confidence, and reason are ignored.

Run each itemizer on the same inputs and compare its output with the expected items:

- **Boundary precision, recall, and F1:** Correctness and completeness of proposed splits.
- **Exact item matches:** Items with identical ordered page membership.
- **Errors:** Locations of extra or missed splits, missing pages, duplicates, or ordering errors.

Derive boundaries from item ranges; exclude the start of the first page from boundary scoring. Keep tuning cases separate from held-out evaluation cases. Include continuations, attachments, poor OCR, and items spanning PDFs.

When neither result has splits, boundary scores are 1. If only one has splits, boundary scores are 0. A valid report exits successfully regardless of score; invalid input or output exits with code 2.

