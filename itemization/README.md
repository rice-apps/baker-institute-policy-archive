# Itemization

Identifies individual documents (“items”) in an ordered collection of OCR pages. A PDF may contain multiple items, and an item may span multiple PDFs.

Itemization runs before AURA to reduce unnecessary processing. A human reviews all proposed items before they proceed.

## Approaches

- **Heuristic:** Uses configurable weights and thresholds for boundary signals such as titles, dates, signatures, and page numbering.
- **LLM:** Uses Claude to analyze consecutive pages and identify item boundaries.
- **Hybrid (planned):** Combines heuristic and LLM methods.
