 Science Policy Archive — Architecture Ideas
Oct 15, 2026 · @Moyinoluwa Orimoloye
This is an ideas doc for the RiceApps × Baker Institute team: a starting architecture for turning Kenny's Box collection into linked, searchable records in InvenioRDM. Nothing here is final. Each section is filled in as we discuss it; empty sections are still open. Comment anywhere to push back.
1. Goals, constraints & scale
We are building a researcher-focused science-policy database that anyone can use, starting with Baker's OSTP/PCAST records (~1,200 docs) and designed to grow to other collections, other universities and ~100M documents. We build for the pilot now, but the decisions below must survive that growth.
Goals
Must-have: ingestion from source collections into InvenioRDM, with entity linking (Wikidata first).
Must-have: search over records, metadata and full text.
Nice-to-have: AI summaries with citations, export to analysis tools (e.g. Atlas.ti), visualization.
Long-term: a durable public resource for anyone studying science and technology policy, beyond Baker's OSTP records.
Timeline
RiceApps development runs late September 2026 to early April 2027, with biweekly client meetings and a fully documented handoff at the end. First coding sprint ends October 24, 2026. The client plans to launch the database with a Baker Institute event and user testing in fall 2027.
Scale
Stage
Documents
Notes
Pilot
~1,200–1,300
Already in Box with descriptive metadata; our test set
Full Baker collection
Growing
All PDFs in Box, in mixed states of processing (see docs-to-process sheet)
Long term
~100M (~10 TB)
Other collections and institutions, on Rice storage

Constraints
AURA is the default parser. It is still being finished (itemization, accessibility checklist), is semi-automated today, and is expensive per page. Its backend API allows batch automation later.
Uploads are controlled. For now only Kenny's team adds documents, through a shared source folder; review is human-in-the-loop.
Accessibility mandate. Published PDFs must meet the accessibility requirements taking effect next year; AURA owns remediation (Section 17).
Handoff. Rice staff, not RiceApps, will run this after April 2027, so it must be operable without us (Section 22).
Resources available: group API keys (AWS, Azure, OpenAI, Anthropic), Rice CRC virtual machine, NOTS GPUs, a dedicated Fondren server, and a project budget.
Design principles
Every stage is an interface. Each pipeline stage has one defined interface covering everything that stage needs. Implementations behind it can be swapped, or run side by side and compared, without touching the rest of the pipeline; no tool, source or destination is hardcoded.
Invenio is the catalog, not the workflow. Pipeline state stays in our Postgres; Invenio receives published items only.
Humans stay in the loop. Automated steps propose; people approve itemization, low-confidence metadata and entity links.
Reprocessing is normal. AURA and extraction will improve, so every stage is repeatable without duplicating records or overwriting human edits.
Pilot-sized build, scale-aware decisions. We run on one server for 1.2k docs, but storage, IDs and orchestration choices must not block 100M.
2. Pipeline overview
Every upload moves through eleven stages, cheapest checks first, so duplicates are caught before the expensive AURA step. For now, itemization runs before AURA; this may change once itemization is discussed (Section 9). Each stage is a separate, retryable step in the orchestrator (Section 6).

ingestion pipeline · 11 stages, 3 duplicate checks, 1 human gate
Detect or upload. A source adapter finds a new or changed file, or receives a direct upload (Section 7).
Fetch and content hash. If the hash matches a stored original, skip processing, record the new source location and notify the uploader. A force option reprocesses anyway.
Store and normalize. Store the original unchanged. Produce a working PDF as a derivative (TIF to JPEG 2000 to PDF, HTML/TXT to PDF; PDFs pass through) and classify the file as born-digital or scanned.
Render pages and page dedupe. Render each page to a small image locally and compute a perceptual hash. Near-duplicate pages are flagged. If every page matches existing pages, the whole upload is flagged and itemization is skipped.
Itemize. Split the whole upload into items (page ranges) using cheap OCR or the existing text layer, then cut per-item PDFs as derivatives.
Item dedupe. Compare item text against existing items; matches are flagged for review.
AURA. Per item: accessible PDF, layout JSON and veraPDF report (Section 8).
Metadata extraction. An LLM extracts fields from the AURA output and source context (Section 10).
Entities. Extract name mentions and link them through entity-linking adapters, Wikidata first (Section 11).
Review. Human gates for splits, flagged duplicates, low-confidence fields and entity links (Section 12).
Publish. Send approved items through export adapters, Invenio first, and update the search indexes (Sections 13 and 15).
Every stage is an interface
Each stage has one interface that defines everything the stage needs: its inputs, its outputs and their confidence and provenance. Implementations of that interface are interchangeable, so we can swap tools, run several on the same documents to compare them, and add new ones without changing the stages around them.
Stage
Interface
Implementations (current or candidate)
Section
Detect or upload
Source adapter
Box, Google Drive, direct upload
7
Store
Storage adapter
Pilot S3-compatible store, Open Storage Network
4
Page and item dedupe
Deduper
Perceptual page hash, text similarity
5
Itemize
Itemizer
Manual, LLM with guidelines, trained classifier, similarity clustering
9
OCR and parsing
Parser
AURA, cheap OCR, other open-source parsers
8
Metadata
Extractor
LLM (provider pluggable), folder-path parser, importer
10
Entities
Linker
Wikidata, later ROR, ORCID, Library of Congress names, local entities
11
Search
Search index
OpenSearch, or Postgres with pgvector
13
Publish
Export adapter
InvenioRDM, Quartex, CSV / JSON, Wikibase
15

The orchestrator (Section 6) only wires these interfaces together, so it can be swapped too.
3. Data model & metadata schema
Pipeline state lives in our own Postgres, in the same cluster as InvenioRDM; Invenio holds only published items. Nothing in the model is tied to Box: every file arrives through a source adapter, and Box is just the first one (Section 7).
Core objects
Object
What it is
Key fields
Lives in
SourceFile
An original file as fetched from a source
Source adapter ID, external reference (e.g. Box file ID + path), checksum, folder-derived metadata
Pipeline DB + file storage
Page
One page of a source file
OCR text, layout JSON reference, OCR confidence
Pipeline DB
Item
The archival unit; becomes one Invenio record
Page ranges (may span several source files), metadata values
Pipeline DB, published to Invenio
Derivative
Files produced for an item
AURA accessible PDF, layout JSON, veraPDF report
File storage, linked from the item
EntityMention
A name as it appears on a page
Surface text, item, page, span, role (author / recipient / mentioned), confidence, link to Entity (nullable)
Pipeline DB
Entity
The canonical person or organization
Canonical label, aliases, external IDs from linking adapters (Wikidata QID first)
Pipeline DB, published to Invenio / Wikibase
Relation
A link between two items
Relation type, provenance
Pipeline DB, published as Invenio related_identifiers

Items and source files are many-to-many by page range: one 2,000-page FOIA file splits into many items, and a folder of TIFs combines into one item.
Why mentions and entities are separate
One person appears many ways: "Dr. Holdren", "John P. Holdren", "the Director", OCR-mangled "J. Ho1dren". Many mentions point to one entity.
The mention is evidence (what the page says, where, in what role); the link to an entity is a judgment. Fixing a bad link is one pointer change and never touches the document record.
Unresolved mentions can exist without an entity, waiting for review, instead of creating a duplicate entity per variant.
Metadata fields: three layers and a field registry
Core: Invenio's built-in DataCite-based fields (title, creators, dates, subjects, description, resource type, rights, related identifiers). Stable.
Project fields: a small set of Invenio custom fields people search and filter on, e.g. spa:administration, spa:source_collection, spa:foia_number, spa:box_folder. Adding one is a config change plus a reindex, so it is deliberate.
Long tail: everything else, stored as JSONB in the pipeline DB. A field moves up to layer 2 once it proves useful for search.
A field registry table defines every field once: type, how it is extracted (LLM prompt hint, imported column, folder-name parse), and how it maps to each destination (Invenio, Dublin Core for Quartex, etc.). Adding a field is one registry row; the extraction prompt and every export mapping are generated from it.
Every stored value records its provenance (import, LLM, or human) and a confidence. Reprocessing never overwrites a human-set value. This lets the existing descriptive metadata on the 1.2k test records serve as ground truth.
Exports
Exports go through export adapters, mirroring source adapters, so records can be sent anywhere: Invenio first, then Quartex (Woodson's digital asset system), CSV / JSON and later Wikibase. Each adapter reads the field registry for its mapping. Details in Section 15.
Item relations
The authoritative relation table is in the pipeline DB; Invenio gets a projection in related_identifiers. Mapping from the itemization guidelines:
Guideline case
Relation
Attachment or enclosure to a memo
attachment IsSupplementTo memo; memo IsSupplementedBy attachment
Handwritten note tied to the next letter
note References letter
Items from the same original folder
folder and order stored as fields, not as records

Communities
An Invenio community is a curated group of records with its own members, roles, landing page and review workflow; a record can belong to several. Communities represent who curates a collection (e.g. Clinton Library FOIA, Neal Lane papers). What a record is about (administration, date, subject) stays in fields, so search can filter across collections. Another university joining gets its own community and curators.
Identifiers
Each item gets an opaque, stable ID. The legacy human-readable name (folder + filename + sequence number) is kept as a secondary identifier. Duplicate detection is covered in Section 5.
4. Storage, provenance & versioning
Records and pipeline state live in Postgres; files live in an S3-compatible object store behind a storage adapter. Originals are copied in, stored immutably by content hash, and every derivative records exactly what produced it. An original is the exact bytes fetched from a source: never modified, and irreplaceable if lost. A derivative is anything produced from an original (OCR text, layout JSON, AURA accessible PDF, per-item PDFs from itemization, thumbnails, veraPDF reports) and can always be regenerated from the original plus a pipeline version.
Storage
Storage adapter. The pipeline reads and writes files only through a StorageAdapter interface (put, get, exists, delete, presigned URL). The first implementation is S3; because most storage systems speak the S3 API, one adapter covers most backends by changing the endpoint.
Invenio uses the same store. InvenioRDM's file storage is pluggable, and its S3 module lets published record files live in an S3-compatible bucket, so pipeline and catalog share one storage layer.
Backends by stage. Pilot: an S3-compatible store hosted on the Fondren server (target home; we may start on another Rice machine such as the CRC VM). The provider is not chosen yet; it depends on what Rice already offers. Long term: Open Storage Network (OSN), NSF-funded research storage with an S3 API, for published files at the 10 TB scale. Because all storage access goes through the adapter, moving to OSN is a configuration change, not a rewrite.
Copy originals in. Source systems can move, rename or delete files, and reprocessing needs the exact bytes. We keep the source reference (adapter, external ID, path) for provenance, but process our own copy.
Layout. Originals are content-addressed by SHA-256 (originals/sha256/ab/cd/<hash>), which makes them immutable and gives exact-duplicate detection for free. Derivatives are keyed by item and pipeline run (items/<item_id>/<run_id>/accessible.pdf).
Provenance
Every artifact records what produced it: the stage, tool and version (AURA version, model name, prompt version), parameters, and the hashes of its inputs. This answers questions like "which items went through AURA before the formula fix?" so only those are reprocessed. Field-level metadata provenance is covered in Section 3.
Versioning
Originals: the same external file arriving with a new checksum becomes a new SourceFile version; the old one is kept.
Derivatives: reprocessing creates a new run beside the old one. Each item has a "current" pointer that flips only once the new output is accepted.
Published records: Invenio's native versioning publishes changed files as a new version under the same parent ID, so citations keep resolving. Metadata-only fixes edit the record in place.
5. Deduplication
Uploads are checked for duplicates at three levels, cheapest first, so repeated content is caught before the expensive AURA step (pipeline stages 2, 4 and 6). Exact matches skip work; near-matches are flagged, never merged and never blocking.
Level
Pipeline stage
Example
Method
On match
Exact file
2. Content hash
Same PDF uploaded twice, or present in two source folders
SHA-256 of the file bytes
Skip processing, record the new source location and its folder metadata, notify the uploader. A force option reprocesses.
Near-duplicate pages
4. Page dedupe
Same memo rescanned, or released in two FOIA productions as separate scans
Perceptual hash of each rendered page
Flag and continue. If every page matches, flag the whole upload and skip itemization.
Near-duplicate items
6. Item dedupe
Same document inside two different uploads, or a born-digital report and its scanned printout
Text similarity (MinHash / LSH) on cheap-OCR text; scales to 100M
Flag for review before AURA runs on it

Each level catches what the one before misses: the content hash catches identical files, the page check catches identical-looking pages in different files, and the item check catches identical text in a different visual form. Near-identical is often not a duplicate: the itemization guidelines treat each annotated draft of a letter as its own item, so reviewers decide between duplicate and related variant. Entity deduplication belongs to entity linking (Section 11).
6. Pipeline orchestration
For pipeline orchestration, I recommend using an existing open-source tool rather than building our own. Two candidates are detailed below: Hatchet and Prefect. Whichever we use, each pipeline stage is a plain Python function behind a thin stage interface, so the orchestrator only wires stages together and can be swapped later.
What the orchestrator must do
Start a run per upload (event-driven), not on a nightly batch.
Retry with backoff, and enforce concurrency and rate limits per external service (AURA, LLM APIs, Wikidata).
Fan out to one task per item.
Rerun from any stage, for reprocessing.
Expose an API our own UI can build on; Kenny's team will use our UI, so the orchestrator's dashboard is for engineers.
Stay light enough for Rice staff to operate after handoff.
Human review and runs
Review can take days and involve several people. Review state lives in our Postgres, where our UI can read it. Whether a run pauses during review and resumes afterwards, or ends and a new run continues, is still open (Section 12).
Designing for 100M documents
At pilot scale any engine works. At 100M documents, each passing through 10+ stages, the orchestrator executes billions of tasks, and three things matter more than the engine choice:
Work unit size. A task is one item or a batch of items, never one page.
A separate database. The orchestrator's Postgres is its own instance, apart from Invenio's and our pipeline DB.
Retention. Run history is pruned on a schedule.
The real throughput limit at that scale is AURA and LLM rate limits, which is why per-service rate limiting is a hard requirement.
Candidate: Hatchet
Hatchet is an MIT-licensed task queue and durable workflow engine that uses Postgres for both its task runtime and its observability.
Pros
Only dependency is Postgres, which we already run: the smallest footprint for Rice to inherit.
Concurrency limits by dynamic key and global or dynamic rate limits, which map directly onto separate limits for AURA, OpenAI and Wikidata.
Durable sleep and event waits, if we ever want an in-workflow pause.
Built-in dashboard, logs and failure alerting (Slack, email).
Cons
Younger project with a smaller community than Prefect.
Less likely to be familiar to Rice staff or future student developers.
Workers connect over gRPC: one more networking detail to configure on Rice machines.
Candidate: Prefect
Prefect is an Apache 2.0 Python orchestration framework; self-hosting is free with no feature gating.
Pros
Mature, widely used, large community; plain Python decorators make stages easy to read.
Global concurrency limits and rate limits, usable around any Python call, including external APIs.
Full UI, schedules, retries, automations and event triggers in the self-hosted version.
Cons
More moving parts: a server, background services, workers and Postgres, with Redis recommended when scaling (self-hosting guide).
RBAC, audit logs and SSO are Prefect Cloud only, so self-hosted access control is on us.
Built around data pipelines; per-file, event-driven runs work but are less central to its design.
Other options
Other options also exist: DBOS, Temporal, Procrastinate, Restate, Inngest, Windmill, Airflow, Dagster, and building our own.
7. Source adapters
Every file enters through a source adapter. Sources come in two kinds, pull (we ask the source what changed, e.g. Box) and push (files arrive at us, e.g. direct upload), but both emit the same event into the pipeline, so nothing downstream knows how a file arrived. Box is the first adapter; polling is enough for the pilot.
Interface
Class
Methods
Examples
SourceAdapter (base)
fetch(ref) streams the bytes; describe(ref) returns name, full path, size, modified time, uploader and the source's own checksum if any; capabilities flags (webhooks, checksums, versions)
All sources
SyncedSource (pull)
Adds list_changes(cursor): files added, changed, moved or deleted since the last sync, plus a new cursor. Run on a schedule
Box, Google Drive, later S3 or OneDrive
PushSource (push)
No listing. Our upload API receives the file, writes it to staging and emits it
Direct upload, a one-off bulk import (zip or disk)

Both kinds emit (source_id, external_ref, metadata) into stage 1, and stage 2 calls fetch() regardless of kind. Each configured source is a row in the pipeline DB: adapter type, root folder, a reference to its credentials, and its sync cursor. Adding Drive means one new adapter class and one config row.
Detecting new files
Pilot: scheduled polling (e.g. every 15 minutes) plus a "sync now" action.
Later: webhooks, where the source supports them. They need a public HTTPS endpoint, which a Fondren or CRC machine may not have.
Push sources trigger ingestion on receipt.
What each change does
Change at source
Action
New file
Ingest through the full pipeline
Content changed
New SourceFile version (Section 4) and reprocess
Moved or renamed
Update the source reference only; the hash is unchanged, so no reprocessing, but folder metadata may change
Deleted at source
Keep our copy and flag it; never unpublish automatically

Box specifics
Folder paths carry metadata (FOIA numbers, box and folder IDs). The adapter stores the path raw; parsing it into fields happens in the metadata stage through the field registry, so adapters stay simple.
Files arriving in one sync from the same folder form a batch, so uploaders get one summary ("42 files ingested, 3 duplicates") instead of 42 notifications.
Ownership
For now only Kenny's team adds documents. How sources map to collections, communities and owners is not settled yet and will be revisited with access control (Section 16).
8. OCR & parsing
OCR and parsing go through parser adapters. Every OCR tool sits behind the same interface, so tools plug in and out and can be evaluated side by side on the same documents.
Parser adapters
Parser.parse(pdf, options) -> ParseResult
  accessible_pdf, layout_json (raw), pages[text, blocks, confidence], report, tool_version
Adapter
Role
AURA
Default for published items: Azure layout and OCR, Mathpix formulas, figure alt text, PDF/UA-2 tagging, veraPDF report
Cheap parser
OCRmyPDF / Tesseract, or the existing text layer for born-digital files; text for itemization and item dedupe before AURA runs
Other open-source parsers
e.g. Docling, olmOCR, Marker; plugged in to compare quality and cost

We plug in, then evaluate: the same test documents run through each adapter and the results are compared (Section 18).
How parser output is used
Each parser's raw output is stored unchanged as a derivative.
We derive our own normalized representation from it (per-page text, blocks with role and position, confidence). Everything downstream reads ours, so changing parsers does not change the rest of the pipeline.
The parser and its version are recorded on every output (Section 4).
Pages with low OCR confidence are flagged to review.
AURA as an independent service
AURA is an independent service maintained by its developer, and likely our default OCR parser. We call it through the parser adapter like any other parser and evaluate it alongside the others. Its current limits (below) are integration points to agree with its developer: an API our services can call, job state that survives restarts, and outputs fetched by job rather than by filename.

AURA today
AURA (repo) is a Spring Boot (Java) backend plus a React UI, about 22k lines, MIT-licensed, v1.0.0 (July 2026), written by one developer.
Area
Current state
Working services
Azure layout/OCR (chunked for 600+ page scans), Mathpix formula merge, PDF/UA-2 tagging with iText (MathML, bookmarks, invisible text layer), figure alt text (OpenAI, Gemini or Claude), veraPDF reports, searchable PDFs, born-digital detection, page-text export
Not in AURA
Itemization, metadata extraction, entities, Invenio integration
Jobs
Held in memory on a 4–16 thread pool; lost on restart
Files
Local disk under {baseDIR}/{username}/projects/..., found by filename conventions
API
Browser-oriented: session-cookie login only, CORS fixed to localhost, outputs fetched by filename
Dependencies
Spring Boot 2.6.6 (past open-source support); iText 9 is AGPL while the repo is MIT
Tests
Only the default Spring context test
Code shape
Logic concentrated in three large classes (2.4k, 2.8k and 1.7k lines)

9. Itemization
Itemization splits one upload into the separate documents (items) it contains. No method is chosen yet: candidates sit behind one itemizer adapter, we try them on the same documents, and keep what works. Running itemization before AURA is preferred because it is cheaper (Section 2); if the candidates that work best need AURA-quality text, it moves after.
What counts as an item
Library staff on the previous team wrote itemization guidelines (April 2026). A new item usually starts with a title or memo header and ends with a signature block; enclosures and attachments are separate items linked to their parent; page-number restarts and changes in formatting signal a new item. The guidelines were never formally signed off, so we confirm them with Kenny before building against them.
Previous attempts
When
Approach
State
Jun–Sep 2025
Clustering by page similarity: embed each page's text, cluster pages, split where similarity drops (repo)
Research notebooks and a demo; never integrated
Spring 2026
GPT-4o (earlier Mistral) prompted with the guidelines, over Azure layout output
Demoed; not finalized while the rules kept changing
Summer 2026
Planned comparison of a trained Azure Document Intelligence classifier against the GPT-4o approach, on test files with known boundaries
Plan only; no results found

Whether a file needs itemization at all was decided by a hand-maintained list. A draft paper claimed a fine-tuned model for this step; none was built.
Itemizer adapter
Itemizer.propose(pages) -> [ItemProposal]
  page_range(s), type, confidence, reason, relations (e.g. attachment-of)
Candidate
How it works
Manual
A person marks the splits in the review UI
LLM + guidelines
Reads cheap-OCR text and page thumbnails, applies the written rules
Trained classifier
e.g. Azure custom classification, trained on already-itemized documents
Similarity clustering
Splits where adjacent pages stop looking alike (the 2025 approach)

High-level thoughts
Not every upload needs splitting. Each source or folder can be marked needs itemization, already itemized, or combine (e.g. a folder of TIFF scans becomes one item); reviewers can override per file.
The model proposes, a person approves. Proposals go to review, at least in the pilot; auto-accept only once evaluation shows it is safe.
Long files (up to ~2,000 pages) are processed in overlapping windows, deciding page by page whether a new item starts, so cost grows linearly with length.
Evaluation: ground truth from collections already itemized by hand, plus test files built by joining known items so the true boundaries are known. Measure boundary precision and recall, and report boundaries between two items of the same type separately, since those are the hard case.
Flag: excluded pages
The previous team proposed (February 2026) dropping blank pages and pages showing only a FOIA withholding notice from itemized items. We have not decided whether to adopt this; see Open questions.
10. Metadata extraction
Metadata extraction fills each item's descriptive fields (title, date, subject, people, description and so on) from its parsed text. Extractors sit behind an adapter, the field registry (Section 3) defines what to extract, and every value carries evidence and a confidence so people can check it quickly.
Previous attempts
Spring 2026: Mistral was prompted with an outline of the item's structure plus its full text, filling title, language, subject, format/genre, administration, date, time span, people and organizations, and description. It produced a report and was never integrated.
The field list kept changing (title coming back as the filename, people and organizations needing separate fields, a source field added). The 28-field list in the old database schema was never finalized.
The ~1.2k test records already carry descriptive metadata (exported from Quartex), which serves as ground truth.
Approach
Extractor adapter. extract(item) -> {field: value, confidence, evidence}, with implementations such as an LLM extractor (provider pluggable: OpenAI, Claude, Gemini or a local model), a path parser for metadata held in folder names, and an importer for metadata that already exists.
Registry-driven. Each field's type, prompt hint and allowed values come from the field registry; the LLM must return JSON matching that schema. Dates are normalized to one standard format that supports ranges and approximate dates; controlled fields (administration, resource type) are limited to fixed lists.
Evidence on every value: the page and a short supporting quote, so a reviewer can verify it in seconds. Values without evidence get low confidence.
Review and provenance. Low-confidence values go to review. Values set by a person or imported never get overwritten on reprocessing (Section 3).
People and organizations are extracted as mentions with roles (author, recipient, mentioned); Section 11 links them to entities.
Evaluation: per-field accuracy against the existing metadata on the test records, compared across providers on quality and cost.
11. Entity linking
Entity linking resolves the people and organizations mentioned in items (Section 10) to canonical entities, linked to outside authorities through linker adapters, Wikidata first. For now we only read from Wikidata, never write to it. A local Wikibase comes after the pilot; adding it later should be easy, since it would be one more export adapter.
Previous plan
The previous team's latest diagram (October 2026): people metadata goes to "match in Wikidata?"; a match links to the Wikidata item, no match creates an entry in a local Wikibase, and the resolved identifiers are stored on the Invenio record. The project's objectives also call for resolving name variants ("Bill Clinton" vs "William J. Clinton").
Building blocks
Our Entity table is canonical. Each entity has our own stable ID; Wikidata QIDs and other authority IDs attach to it as "same as" links, so no single outside source is a dependency.
Linker adapter. candidates(mention, context) -> [{source, id, label, description, score}]. Wikidata first; later candidates include ROR (organizations), ORCID, the Library of Congress name authority file / VIAF, and our own local entities.
Wikibase later, without rework. Nothing in the core model depends on Wikibase. Publishing local entities to a Wikibase instance post-pilot is an export adapter (Section 15) added when needed.
One proposed method
There are many ways to do this; this is one starting point.
Group variants within the corpus ("J. Holdren", "John P. Holdren") so each name is looked up once. Not needed for v1.
Generate candidates from each linker adapter.
Disambiguate with document context: the document's date against the person's dates and positions held (Wikidata records office tenure, e.g. OSTP director), the role in the document, and organizations mentioned nearby.
Use a seed list of known people (OSTP and PCAST staff since 1989) to make most links near-certain, if such a list is built.
Decide: high confidence links automatically, medium goes to review, no match creates a new local entity pending review.
Reconciliation: matching runs in code through the Wikidata reconciliation service (the same API OpenRefine uses). OpenRefine remains optional for librarians who prefer cleaning a batch by hand, with results re-imported as human-provenance values.
Evaluate linking precision and recall on a hand-labelled sample, separately from extraction accuracy (Section 10).
12. Human-in-the-loop review
The goal is to automate as much as possible at the highest fidelity; review is where automation is not confident enough. Everything the pipeline flags goes into one review queue, and review state lives in our database so several people can work on the same item over time.
What gets reviewed
Task
Comes from
Possible duplicate
Page and item dedupe (Section 5)
Itemization proposal
Itemizer (Section 9)
Low-confidence OCR page
Parser (Section 8)
Low-confidence metadata value
Extractor (Section 10)
Entity link or new entity
Linker (Section 11)
File deleted at source
Source adapter (Section 7)
Publish approval
Final gate before export

Approach
One review model in the pipeline database: the proposal, its confidence and evidence, status, and who decided what and when. The unit of a review task is not decided yet (per item, per field, per page boundary or per mention).
Review history is appended to the item. Every touch by every reviewer is recorded as an event, so the item keeps one timeline. Human decisions are stored as human-provided values, which reprocessing never overwrites.
A view per task type in our UI: page thumbnails with split markers for itemization, a field beside its evidence highlighted on the page for metadata, the mention in context beside candidates for entities, and side-by-side pages for duplicates. Built for fast batch review.
Configurable gates. Thresholds per task type and field decide what must be reviewed before publishing and what can be fixed after. Evaluation tells us where automation is reliable enough to loosen them.
Consideration: pause and resume, or a new run after review
When review finishes, it fires an event that continues the pipeline. That event can either resume the paused run or start the next one; this is open.


Pause and resume one run
Run ends; approval starts a new run
History
One run holds the item's whole timeline
Several runs, joined by item ID
Long waits
Runs stay open for days or weeks
Runs stay short
Deploying code changes
Paused runs must survive changes to workflow code, a common pain point
No issue; new runs use new code
Reprocessing mid-review
Awkward; a paused run must be cancelled or modified
Natural; start a fresh run
Orchestrator
Needs durable waits (Hatchet has them; Prefect's are weaker)
Works with any orchestrator

Because review state and history live in our database either way, the item keeps a single timeline under both options; the choice is mainly about how the orchestrator behaves, and can follow the orchestrator decision (Section 6).
13. Search & discovery
Search is a must-have, built in layers over our own search API. Our pipeline database stays the source of truth; Invenio and the search indexes are both downstream copies of it, linked by IDs. The indexes will likely live in OpenSearch as separate indexes of our own, which we still need to confirm.
Layers
Layer
What it finds
How
1. Catalog search
Items by metadata, with filters (administration, date, type, collection, people)
Our own items index
2. Full-text search
Exact words anywhere in the OCR text
A page-level index; results grouped by item, opening the PDF at the matching page
3. Semantic search
Passages about a topic even when the wording differs
Embeddings per passage combined with keyword ranking (hybrid search)
4. Entity browsing
Everything mentioning a person or organization, and who appears with whom
The entity links from Section 11
5. Q&A with citations
Answers that cite item and page
Retrieval combining layers 1–4, plus an LLM; never answers without a source

There is a lot we can add later to make Q&A better; for now, layers 1–4 are the primitives it builds on.
A page-level index does not require choosing a page or item first. Each page is its own entry carrying its item ID, page number and copies of the item's filter fields, so one query searches every page of every item, and results are grouped by item.
From publish to index
The publish step records an event; one consumer pushes the record to Invenio, others update the search indexes. Every consumer can rebuild entirely from our database, so a broken index or a new chunking method means reindexing from source.
We link to Invenio by record ID only, and do not query Invenio's internal search index: its schema is Invenio's to change, and our UI needs layers 1–4 behind one API. Invenio's own search keeps working on Invenio's pages.
Edits happen in our system and are pushed to Invenio, never the other way, so there is one source of truth.
Indexes
InvenioRDM already requires OpenSearch, which handles keyword search, vector search and hybrid ranking at large scale. The proposal is separate indexes of our own, in the same cluster for the pilot and a dedicated cluster when load justifies it. Postgres with pgvector is the alternative for the pilot.
Index
One entry per
Used for
Items
Published item
Catalog search, filters and facets
Pages
Page
Full-text search
Passages
Paragraph, for now
Semantic search; stores the embedding and the model that produced it
Entities
Person or organization
Name lookup and entity browsing; co-occurrence stays in Postgres

Every entry carries an access level so restricted items can be filtered out (Section 16). A new version of an item replaces its old entries.
Semantic search
Semantic search is the least straightforward layer and the one with the most room to optimize.
Evals come first. Each combination of chunking method and embedding model gets its own index version, switched with an alias, so variants can be compared on the eval set and rolled back quickly. Paragraph chunks are the starting point; semantic and LLM-based chunking are variants to test for cost and accuracy.
Vector index. At our target scale we need approximate nearest-neighbour search (OpenSearch supports graph-based HNSW and cluster-based IVF indexes, with compression). These trade recall against memory and against how quickly new entries become searchable, so those trade-offs belong in the evals too.
Clustering. Grouping passages by topic could serve both the vector index and browsing ("documents like this").
Evaluation
Kenny has search test cases; we turn them into a query set with judged results and compare keyword, semantic and hybrid search with standard ranking metrics.
14. Application (web app and backend API)
The application is the full-stack layer people use to reach the rest of the system: our own web app, built from day one in Next.js with Baker Institute branding, and a backend API that is the single doorway to the pipeline, review state, Invenio and the search indexes. Users never see those systems' own interfaces.
Who uses it
Audience
Needs
Public researchers
Search, browse, read items, export sets of documents
Kenny's team
Add documents, watch ingestion, review flagged work, curate collections
Engineers and admins
Configure sources and fields, see failures, rerun stages

Main surfaces
Discovery (public)
Search and browse: one search across the layers in Section 13, with filters and results grouped by item.
Item page: a page viewer that opens the item's accessible PDF at the matching page, alongside metadata, linked entities, related items (attachments, variants) and provenance.
Entity pages: a person or organization, the documents they appear in, and who they appear with.
Ingestion workflow (staff)
Each stage of the pipeline (Section 2) gets its own view, so staff can see and act on every step; review tasks (Section 12) appear in the view for the stage that raised them.
Stage
View
Sources and uploads
Configure sources, upload files, see what has arrived
Pipeline status
Where each file is, what failed, rerun a stage
Duplicates
Flagged files, pages and items side by side; confirm duplicate or related variant
Itemization
Page thumbnails with proposed splits to adjust and approve
OCR and parsing
Page viewer to check text quality on flagged pages
Metadata
Each field beside its evidence on the page; accept or correct
Entities
Mention in context beside candidate matches; link, create or reject
Publish
Items ready to publish; final approval and export status

Admin
The field registry, adapter settings and bulk reprocessing.
Backend API
Single doorway. Every surface goes through one backend API; the web app never calls Invenio, OpenSearch, the orchestrator or storage directly. This keeps those systems swappable.
What it exposes: search across the layers in Section 13, item and entity pages, uploads (the push source in Section 7), ingestion status, review tasks and decisions, and admin actions such as reprocessing.
Same language as the pipeline (likely Python), so it shares the data model and adapters.
Later: if researchers want programmatic access, a public, read-only version of the API can follow.
High-level thoughts
Public and staff areas share one app. Public pages need no login; staff sign in with Google restricted to the rice.edu domain for now, with roles from Section 16.
Design system. Built on an existing accessible component library, themed to Baker Institute branding, so the frontend team owns the look and behaviour.
The app itself must be accessible (WCAG 2.1 AA), not only the PDFs (Section 17).
Pilot order: the ingestion workflow views first, since Kenny's team needs them to load the test records; discovery pages next. The page viewer is shared: the item page uses it for reading, and the ingestion views use it for checking OCR and itemization. As a stretch goal it can overlay layout boxes, OCR confidence and entity highlights from our normalized parser output (Section 8). AURA's existing viewer is a debugging tool tied to AURA's API, so we build our own, carrying over ideas such as colour-coding by category and confidence.
15. Export adapters
Everything the pipeline produces can be exported, and every destination, including Invenio, is an export adapter. What is exportable is defined once; each adapter picks the parts it needs and maps them to its destination's format.
What can be exported: the item bundle
An item's export bundle holds the products of the pipeline:
Part
Contents
Files
The item's original pages, accessible PDF and other derivatives
Text
OCR text per page, and the normalized layout
Descriptive metadata
Every field in the field registry (Section 3)
Entities
Mentions with roles, and linked entities with their outside IDs (e.g. Wikidata)
Relations
Links to other items (attachments, variants, same folder)
Provenance
Source, processing history, tool versions, accessibility report

The bundle is deliberately broad so new destinations need no pipeline changes. Entities can also be exported on their own, without items.
Export adapter interface
One abstract interface, with a concrete implementation per destination.
ExportAdapter (abstract)
  export(bundles)          # create or update items there; returns each item's ID in the destination
  withdraw(item_ids)       # unpublish items exported earlier
Each adapter receives the full bundle and decides what to use. Bundles load lazily, so files are only fetched from storage if an adapter actually reads them.
Shared machinery around the adapters, written once: building bundles from our database, mapping fields to each destination's schema through the field registry, remembering each item's destination ID and last exported version (so a re-export updates rather than duplicates), triggering on publish or on demand, and keeping restricted items out of public destinations (Section 16).
Implementations in scope
Implementation
Uses
export
withdraw
InvenioRDM
Files, metadata, entities, relations
Creates or updates the record through Invenio's API; a new version when files change
Marks the record removed, leaving a notice so citations still resolve
Quartex (likely)
Files, metadata mapped to Dublin Core
Through an API or a batch import file, to confirm
To confirm
CSV / JSON
Whatever the user selects
Writes a downloadable file
Not applicable; files are one-off snapshots
Wikibase (post-pilot)
Entities
Creates or updates entities
Deprecates the entity

Adding a destination means writing one new implementation; the pipeline and bundle do not change.
16. Access control & roles
The public uses the archive anonymously; staff sign in with Google restricted to rice.edu. Each upload is marked public or restricted with a simple toggle, and the items created from it inherit that setting.
Roles
Role
Who
Can do
Public
Anyone, no login
Search, read and download public items
Reviewer
Kenny's team
Upload, review flagged work, approve publishing
Admin
Engineers, and Kenny if wanted
Everything above, plus sources, field registry, adapters and reprocessing

Signing in proves someone is from Rice; it does not grant a role. Roles are assigned in our database.
Public or restricted
A toggle on each upload sets it to public or restricted (staff only). Items created from that upload inherit the setting.
Enforced in one place, the backend API (Section 14). Search indexes store the setting so restricted items are filtered out (Section 13), exports never send restricted items to public destinations (Section 15), and Invenio marks them restricted on its side.
Finer control later (per item, or embargoed until a date) can extend the same setting.
Other points
Anonymous access for the public. Optional public accounts may come later if the team wants to know who uses the archive; anonymous access stays either way.
Audit trail: who uploaded, reviewed, approved, published or changed access, and when, largely from the review history (Section 12).
Machine access: the orchestrator, adapters and parser services use service accounts with their own credentials, never a person's login (Section 20).
Later: if other institutions join, roles become per collection (e.g. a curator for one collection only).
17. Accessibility compliance
PDF accessibility (tagging, alt text, PDF/UA-2 and WCAG conformance) is handled by AURA's developer and is out of our scope for now. Our scope is making our own web app accessible and carrying AURA's results through the pipeline.
Context
The DOJ rule under ADA Title II requires web content, including PDFs, to meet WCAG 2.1 Level AA. In April 2026 the deadlines were extended by a year, to April 26, 2027 for public entities serving 50,000 or more people (source). Title II covers public entities, so how it applies to Rice, a private university, is a question for Rice.
Our scope
The web app meets WCAG 2.1 AA: automated checks in CI, plus keyboard and screen-reader testing of the main pages (Section 14).
Accessibility reports are kept: each item's report from the parser is stored with it (Section 4).
Failures are flagged: items whose accessible PDF fails its check go to review rather than being published silently (Section 12).
Out of scope for now
Making PDFs compliant, including tagging, alt text and remediation of hard cases. This sits with AURA, an independent service maintained by its developer (Section 8).
18. Testing & evaluation
Testing starts on day one: every stage is tested on its own, the whole pipeline is tested end to end, and both run in CI. Quality evaluation for each stage is defined in that stage's section; this section covers how it all fits together.
Layers
Layer
What it checks
When it runs
Unit tests
Individual functions and components
Every change, in CI
Interface contract tests
Every implementation of a stage interface (Section 2) behaves as the interface promises; one shared test suite per interface, run against each implementation
Every change, in CI
End-to-end tests
A small fixed set of documents runs through the whole pipeline, from source to published record and search
Every change in CI, with external services stubbed; with real services on a schedule
Quality evaluations
Accuracy of each stage on its test set (dedupe, itemization, OCR, metadata, entities, search), with cost and time
On a schedule, and whenever an implementation, prompt or model changes

Principles
Fixtures from real documents: a small, versioned set of representative files (typed memos, scans with handwriting, formula-heavy reports, multi-document FOIA files) shared by end-to-end tests and evaluations.
Stubs for expensive services: AURA, LLM APIs and Wikidata have stub implementations of their interfaces returning recorded outputs, so CI is fast, free and repeatable.
Regressions are caught before deploying: a change that lowers a stage's evaluation score is visible before it ships.
Review decisions grow the test sets: human corrections (Section 12) become new labelled examples.
19. Cost
We do not know much about cost yet, so for now we record it. Every call to a paid service (OCR, formula recognition, LLMs, embeddings) stores what it consumed (pages, tokens, model) with the run's provenance (Section 4), so cost per page, per item and per stage can be measured from the pilot and used to guide later choices.
20. Infrastructure, deployment & secrets
For now everyone runs the system locally, using a shared container image so setup is the same on every machine. Rice infrastructure (likely the Fondren server) comes later; we will request access when we need it.
What runs
Component
Notes
Postgres
Pipeline database; the orchestrator gets its own database
S3-compatible storage
Originals and derivatives (Section 4)
OpenSearch
Our indexes; InvenioRDM needs it too
InvenioRDM
Brings its own web, worker, cache and queue services
Orchestrator and workers
Run the pipeline stages
Backend API and web app
The application (Section 14)
AURA
Independent service; hosting to agree with its developer

Deployment
Local first: a container setup that brings up the whole stack on a laptop, so development is quick to start.
Configuration from environment settings, not code, so moving to Rice machines or to Open Storage Network is a configuration change.
Later: a Rice-hosted deployment, likely the Fondren server. Where the public web app is hosted is still to be decided, but likely Rice.
Scripted, documented setup so Rice staff can rebuild it after handoff (Section 22).
Backups cover Postgres and storage; search indexes and Invenio records can be rebuilt from them (Section 13).
Secrets
Code reads secrets only from environment variables, so the store behind them can change.
Secrets never go in code, docs or chat. Each service gets its own keys with the least access it needs, separate for development and production.
Free stores to choose from: Supabase Vault (a Postgres extension, natural if we use Supabase), Infisical (open source, free hosted tier) or SOPS (encrypted file in the repo, no extra service).
Reminder for later: API keys and a shared password from the previous project sit in plain text in the old Drive folder, and a credentials file is committed to a public repo from the previous team. These need rotating before production.
21. Observability
Kenny's team sees pipeline progress and failures in our own ingestion views (Section 14); engineers need to find out quickly why something failed. We start simple and keep it extensible, so we can add or swap tools based on what we learn.
For engineers
Structured logs carrying run, file and item IDs, so one item's journey can be traced across stages and services.
The orchestrator's dashboard (Section 6) for run status, retries and failures.
A few key numbers: files processed, failures by stage, queue backlog, cost (Section 19) and accessibility-check failures.
Health checks for every service, including AURA and outside APIs.
Alerts when a stage fails repeatedly or a service is down (e.g. email or Slack).
Extensible by design
Logs, numbers and alerts go through standard, vendor-neutral formats (e.g. OpenTelemetry), so tracing across services and dashboards (e.g. Grafana) can be added later without changing pipeline code.
22. Handoff & maintainability
Development ends in early April 2027 with a fully documented handoff. After that, Rice's flex engineers maintain the system, so the repository has to be in great shape: easy to understand, safe to change and runnable without us.
Approach
Code in a Rice-owned GitHub organization, not personal accounts, so it outlives the team.
Documentation as we go, not at the end: this architecture doc kept current, a README per service, short decision records explaining why we chose things (orchestrator, search engine and so on), and runbooks for routine jobs (deploy, add a source, reprocess items, restore from backup, rotate keys).
Conventions for agentic development. We iterate on CLAUDE.md, AGENTS.md and other convention files that capture the codebase's principles, so AI coding agents follow them, avoid low-quality generated code and keep the code readable. The same files help human maintainers.
Common tasks without code: adding sources, editing fields, reprocessing and managing reviewers go through the admin views (Section 14).
Tests and CI as the safety net (Section 18), so maintainers can change things with confidence.
Fewer moving parts: well-known open-source tools, nothing only we know how to run, and the interface-per-stage design (Section 2) so future teams can replace parts one at a time.
Handoff sessions with the flex engineers, and a handoff checklist tracked from early on.
Open questions
☐ Administrative vs primary documents. Sean's itemization guidelines split documents into primary (the historical material) and administrative (created to manage records: FOIA cover letters, withholding/redaction notices, transfer sheets, separator pages). Should administrative documents be items in the catalog, tagged with a document_class field and hidden from default search, or kept out of the catalog entirely? Withholding notices tell researchers what is missing, which argues for keeping them.
☐ Derivative retention. How long do we keep superseded derivatives (old AURA outputs, old layout JSON) after a reprocessed version is accepted? Keep the last N runs, or a time window?
☐ Storage capacity at scale. Copying originals in means roughly 10 TB at full scale, plus derivatives. We propose Postgres for records and pipeline state alongside an S3-compatible object store for files. Can Rice provide capacity and hosting for both, and on which machines?
☐ S3 provider. Does Rice already run an S3-compatible storage service we can use for the pilot, or do we self-host one on the Fondren server?
☐ Box authentication. Reading the shared Box folder server-side needs a Box app (a service account added to the folder), which usually requires approval from a Rice Box admin. Who requests it, and how long does approval take? This blocks the first source adapter.
☐ iText licence. AURA is MIT-licensed but depends on iText 9, which is AGPL. Does Rice accept AGPL obligations for AURA, or does it need a commercial iText licence before AURA is distributed to other institutions?
☐ Excluded pages. The previous team proposed dropping blank pages and withholding-notice-only pages from itemized items. Do we adopt this, and if so, are those pages kept as marked-omitted rather than deleted?
☐ Metadata field list. Finalize the list of metadata fields, their definitions and allowed values with Kenny.
☐ LLM API approval. Are we approved to send document text to commercial LLM APIs (OpenAI, Anthropic, Google) for extraction? Does any material, such as FOIA releases, need review first?
☐ Wikibase on the Fondren server. Can the Fondren server host a Wikibase instance after the pilot, and what resources would it need?
☐ OSTP/PCAST staff list. A curated list of OSTP and PCAST staff since 1989 does not seem to exist yet. Is building it in our scope, or will Kenny's team provide it?
☐ Review workload. Who on Kenny's team will review, and roughly how many hours a week? This decides how strict the review gates can be.
☐ Search engine. Confirm OpenSearch (separate indexes of our own) as the search and vector store, versus Postgres with pgvector for the pilot.
☐ Search test cases. Get Kenny's search test cases to build the evaluation query set.
☐ Quartex export. Do we export to Quartex, and does it have an API we can use, or only batch import?
☐ Public accounts. Does Kenny's team want optional public accounts, to know who uses the archive? Anonymous access stays either way.
☐ PDF accessibility ownership. Confirm with AURA's developer that PDF compliance stays with AURA.
☐ Rice accessibility requirements. Does Rice have its own digital accessibility policy or deadline that applies to this project?
☐ AURA integration. Agree with AURA's developer how our pipeline calls AURA: service API and authentication, where it is hosted, throughput limits, job persistence, and how we hear about changes to its output.
☐ Budget. What is the budget for paid services, which accounts pay for them, and are there spending caps today?
☐ Secrets store. Pick a free secrets store for the pilot: Supabase Vault, Infisical or SOPS.
☐ Public hosting. Where is the public web app hosted (likely Rice), and can it be reached from outside Rice?
☐ Open source. Will our code be open source, and under what licence? This also affects the iText licence question.

