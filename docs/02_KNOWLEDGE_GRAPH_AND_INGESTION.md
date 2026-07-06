# Nidarsha Knowledge Graph & Ingestion Architecture

## Purpose

This document defines the first core architecture layer of Nidarsha: the policy ingestion system and knowledge graph.

The goal is to convert scattered government policy sources into a structured, traceable, updateable, and queryable policy knowledge base.

This layer should serve as the foundation for future components such as chat, dashboards, workflows, recommendations, eligibility checks, and policy monitoring.

---

# Scope

This document covers:

* Source websites and references
* Document ingestion
* Metadata tracking
* Idempotency
* Policy versioning
* Knowledge graph structure
* Knowledge graph updates
* Entry points for the rest of the system

This document does **not** fully define:

* Chatbot behavior
* Recommendation engine logic
* User dashboard design
* Workflow automation
* Authentication
* Paid features
* Deployment architecture

Those will be handled separately.

---

# Core Principle

Nidarsha should never treat government policy documents as plain text only.

Each policy source should be converted into structured knowledge with traceable evidence.

Every extracted fact should ideally answer:

* What policy does this belong to?
* Where did this information come from?
* When was it extracted?
* Is it still current?
* What official source supports it?
* Has it changed since the previous version?

---

# High-Level Architecture

```text
Official Sources
    ↓
Source Registry
    ↓
Ingestion Jobs
    ↓
Raw Artifact Store
    ↓
Document Parser
    ↓
Structured Extraction Layer
    ↓
Policy Knowledge Store
    ↓
Knowledge Graph
    ↓
Query / Retrieval Interface
    ↓
Chat, Dashboard, Workflow, Recommendation Engine
```

---

# Source Registry

The source registry stores all websites, pages, PDFs, portals, circulars, and policy references that Nidarsha tracks.

For the initial MSME India focus, examples may include:

* Ministry of MSME websites
* DC MSME scheme pages
* Udyam registration references
* Scheme guideline PDFs
* Office memorandums
* Circulars
* State MSME department portals
* Credit guarantee / subsidy / technology upgradation scheme documents
* Application portal links

Each source should be tracked independently.

## Source Metadata

Each source record should contain:

```text
source_id
source_type
source_name
official_url
owning_department
jurisdiction
sector_scope
language
update_frequency_expected
status
first_seen_at
last_checked_at
last_changed_at
last_successfully_ingested_at
checksum
content_hash
etag
last_modified_header
notes
```

## Source Types

```text
website_page
pdf_document
excel_document
api_endpoint
notification
circular
guideline
scheme_portal
application_portal
manual_entry
```

---

# Raw Artifact Store

All original downloaded artifacts should be preserved.

This is important for:

* auditability
* re-processing
* debugging
* legal/source traceability
* version comparison
* reproducibility

Raw files should not be overwritten.

Suggested structure:

```text
artifacts/
  raw/
    sources/
      <source_id>/
        <ingestion_run_id>/
          original.pdf
          original.html
          metadata.json
          headers.json
```

Each ingestion run creates a new immutable snapshot if the source content changed.

---

# Idempotency

Ingestion must be idempotent.

Running the same ingestion job multiple times against unchanged content should not create duplicate policies, duplicate facts, or duplicate graph nodes.

Idempotency should be based on:

```text
normalized_url
source_id
content_hash
document_hash
policy_id
section_id
fact_hash
relationship_hash
version_number
```

## Hashing Strategy

Recommended hash layers:

```text
source_hash        = hash(normalized URL + source metadata)
content_hash       = hash(raw downloaded content)
document_hash      = hash(clean extracted document text)
section_hash       = hash(policy_id + heading path + normalized section text)
fact_hash          = hash(policy_id + fact_type + normalized fact value + evidence reference)
relationship_hash  = hash(source node + relationship type + target node)
```

This allows the system to detect:

* unchanged source
* changed source content
* changed parsed text
* changed extracted fact
* changed relationship

---

# Ingestion Flow

## Step 1: Source Discovery

Sources can enter the system through:

```text
manual source registry entry
crawler-discovered official links
uploaded documents
admin-added references
future API connectors
```

Initially, manual curation is acceptable and probably preferred.

## Step 2: Source Fetching

The ingestion worker checks each registered source.

For each source:

```text
normalize URL
fetch headers
check ETag / Last-Modified if available
download content if changed or unknown
calculate content hash
store raw artifact
record ingestion attempt
```

## Step 3: Document Parsing

The parser converts source content into structured document text.

For PDFs, extracted structure should preserve:

```text
title
headings
subheadings
paragraphs
tables
lists
page numbers
links
footnotes
references
```

For HTML pages, extracted structure should preserve:

```text
page title
headings
body sections
tables
links
download references
last updated text
```

## Step 4: Policy Identification

The system determines whether the document represents:

```text
new policy
new version of existing policy
supporting document for existing policy
circular updating an existing policy
application guideline
FAQ
portal reference
unrelated document
```

This step may use AI assistance, but the final mapping should be reviewable.

## Step 5: Structured Extraction

The system extracts policy facts such as:

```text
policy name
short name
owning ministry
department
jurisdiction
target beneficiaries
MSME category
sector
location eligibility
business stage
benefits
subsidy amount
credit support
required documents
application process
deadlines
official links
exclusions
definitions
related schemes
```

Each extracted fact should retain evidence.

Evidence should include:

```text
source_id
document_id
version_id
page_number
section_heading
text_span
extraction_method
confidence
```

---

# Knowledge Graph Structure

The knowledge graph should model policies as connected entities, not isolated documents.

## Core Nodes

```text
Policy
Scheme
Department
Ministry
Jurisdiction
Sector
BeneficiaryType
MSMECategory
EligibilityCriterion
Benefit
RequiredDocument
ApplicationStep
Deadline
OfficialPortal
SourceDocument
PolicyVersion
Notification
Circular
FAQ
Definition
```

## Example Relationships

```text
Policy BELONGS_TO Department
Department PART_OF Ministry
Policy APPLIES_TO Sector
Policy TARGETS BeneficiaryType
Policy HAS_ELIGIBILITY EligibilityCriterion
Policy PROVIDES Benefit
Policy REQUIRES_DOCUMENT RequiredDocument
Policy HAS_APPLICATION_STEP ApplicationStep
Policy HAS_DEADLINE Deadline
Policy LINKS_TO OfficialPortal
Policy SUPPORTED_BY SourceDocument
Policy HAS_VERSION PolicyVersion
Notification UPDATES Policy
Circular CLARIFIES Policy
Policy RELATED_TO Policy
Policy DEPENDS_ON Policy
Policy COMPLEMENTS Policy
```

---

# Policy Versioning

Policies change over time.

Nidarsha should avoid treating a policy as one static record.

Suggested model:

```text
Policy
  └── PolicyVersion
        ├── SourceDocument
        ├── ExtractedFacts
        ├── EligibilityRules
        ├── Benefits
        └── ApplicationSteps
```

A policy can have multiple versions.

Only one version should usually be marked as current.

Important fields:

```text
policy_id
version_id
effective_from
effective_to
is_current
source_document_id
created_from_ingestion_run_id
change_summary
supersedes_version_id
```

---

# Update Strategy

When a source changes, the system should not blindly overwrite existing knowledge.

Instead:

```text
detect content change
parse new version
extract candidate facts
compare with previous version
create diff
mark changed facts
update current policy version only after validation
preserve previous version
```

Possible change types:

```text
new_policy
policy_removed
policy_renamed
eligibility_changed
benefit_changed
deadline_changed
document_requirement_changed
application_process_changed
source_link_changed
minor_text_change
formatting_only_change
```

---

# Human Review Layer

For early versions, human review should exist before important graph updates are promoted.

Suggested statuses:

```text
extracted
needs_review
approved
rejected
superseded
archived
```

AI can assist extraction, but policy facts should be reviewable because users may rely on them for real decisions.

---

# Storage Recommendation

The system may use multiple storage layers.

## Raw Artifact Storage

For original files:

```text
local filesystem for development
S3-compatible object storage for production
```

## Relational Database

For metadata, ingestion runs, source registry, policies, versions, and review status:

```text
PostgreSQL
```

## Vector Store

For semantic search and retrieval:

```text
pgvector
```

## Knowledge Graph

Initial practical option:

```text
PostgreSQL tables modeling graph nodes and edges
```

Later option:

```text
Neo4j or another graph database
```

Recommended approach:

Start with PostgreSQL + pgvector.

Move to a dedicated graph database only when graph traversal requirements become too complex.

---

# Suggested Core Tables

```text
sources
ingestion_runs
raw_artifacts
documents
document_versions
policies
policy_versions
policy_facts
policy_sections
policy_entities
policy_relationships
evidence_spans
review_queue
embedding_chunks
```

---

# Entry Point for Rest of System

Other Nidarsha components should not directly read raw documents.

They should interact with the knowledge layer through stable service interfaces.

Initial entry points:

```text
PolicySearchService
PolicyDetailService
PolicyGraphService
EligibilityContextService
EvidenceRetrievalService
PolicyUpdateService
```

## Example Use Cases

Chat uses:

```text
search policies
retrieve relevant chunks
retrieve evidence
retrieve policy facts
```

Dashboard uses:

```text
get policy overview
get eligibility
get benefits
get required documents
get official links
get related policies
```

Recommendation engine uses:

```text
match user profile to eligibility criteria
rank policies
explain recommendation
retrieve supporting evidence
```

Workflow engine uses:

```text
map uploaded document data to eligibility fields
identify missing documents
identify missing criteria
suggest next steps
```

---

# API Boundary

A future API may expose endpoints such as:

```text
GET /policies
GET /policies/{policy_id}
GET /policies/{policy_id}/versions
GET /policies/{policy_id}/evidence
GET /policies/{policy_id}/related
GET /policies/search
POST /policies/match
POST /ingestion/sources
POST /ingestion/run
GET /ingestion/runs/{run_id}
GET /review/queue
```

At this stage, these are architectural entry points only, not final API contracts.

---

# First Implementation Milestone

The first working version should be small.

Recommended MVP ingestion target:

```text
5–10 official MSME policy PDFs or pages
manual source registry
download and store raw artifacts
parse text and tables
extract basic metadata
create policy records
create policy sections
create embeddings
create simple relationships
serve policy search and detail retrieval
```

Do not start with full automation.

Start with a controlled ingestion pipeline that can be inspected, debugged, and improved.

---

# Non-Goals for Version 1

Version 1 should not attempt:

```text
fully autonomous crawling of all government websites
automatic legal interpretation
guaranteed eligibility decisions
production-grade application filing
multi-language support
real-time policy monitoring
complex graph reasoning
paid feature architecture
```

---

# Key Design Decisions

## Decision 1: Preserve raw sources

All original documents must be stored before extraction.

Reason: policy recommendations must remain traceable and auditable.

## Decision 2: Separate extraction from approval

AI-extracted facts should not automatically become trusted facts.

Reason: government policy information can affect real business decisions.

## Decision 3: Start with PostgreSQL

Use PostgreSQL for metadata, graph-like relationships, and pgvector search in the first version.

Reason: simpler deployment, easier open-source setup, fewer moving parts.

## Decision 4: Treat chat as a consumer

The chat interface consumes the knowledge graph. It does not own policy knowledge.

Reason: the same policy intelligence should power chat, dashboards, workflows, and recommendations.

---

# Open Questions

These need further discussion:

```text
Should the first version include only central government MSME policies?
Should state-level schemes be included immediately or later?
How much human review is required before a fact is trusted?
Should policy extraction schemas be fixed or flexible?
Should we support Hindi/regional languages in the first release?
Should the graph use strict ontology definitions from day one?
How should outdated policies be displayed to users?
```

---

# Summary

The ingestion and knowledge graph layer is the foundation of Nidarsha.

Its job is to transform official policy sources into structured, versioned, explainable, and reusable policy knowledge.

Every other system component should depend on this layer rather than parsing government documents independently.

The first version should prioritize correctness, traceability, idempotency, and maintainability over full automation.
