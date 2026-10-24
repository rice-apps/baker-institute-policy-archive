# Baker Institute Science Policy Archive

A researcher-focused, searchable database of science and technology policy documents, built by RiceApps with Rice's Baker Institute. It starts with Baker's OSTP/PCAST records (~1,200 documents) and is designed to grow to other collections, other institutions and ~100M documents.

The system ingests documents from source collections (Box first), runs them through a pipeline (deduplication, itemization, OCR via AURA, metadata extraction, entity linking against Wikidata, and human review), and publishes approved items to [InvenioRDM](https://inveniordm.docs.cern.ch/) and our own search indexes. Researchers use a public web app to search and read; Baker staff use it to manage ingestion and review.

## Status

Early development (RiceApps, September 2026 – April 2027). The architecture is still being discussed and nothing in it is final.

## Repository layout

| Path | Contents |
|---|---|
| [`design/`](design/) | Design docs, starting with the [high-level design](design/high-level-design.md) |
| [`.github/CODEOWNERS`](.github/CODEOWNERS) | Required reviewers for changes to `main` |

More structure (services, pipeline, web app) will be added as code lands.

## Contributing

`main` is protected: all changes go through a pull request and need approval from a code owner (see [CODEOWNERS](.github/CODEOWNERS)).

## Team

RiceApps × Baker Institute for Public Policy, Rice University.
