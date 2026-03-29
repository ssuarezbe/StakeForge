# Release 2 — RAG-Enriched Personas (PageIndex + DuckDB FTS + Dolt)

**Iteration:** 2  
**Codename:** R2  
**Depends on:** Release 1 (`spec/release-1-prompt-mvp-tinytroupe.md`)  
**Maps to:** `why.md` — Phase 3 (RAG-Enriched Personas), **Alt B: hybrid PageIndex + DuckDB FTS** (no vector database)

---

## 1. Release goal

Ground each stakeholder interaction in **ingested primary sources** (transcripts, emails, canvas exports) using:

- **[PageIndex](https://github.com/VectifyAI/PageIndex)** — hierarchical, **vectorless**, reasoning-oriented document indexing (Markdown via `--md_path`; tree / agentic retrieval patterns per project docs).
- **[DuckDB](https://duckdb.org/) FTS** — lexical full-text retrieval over stored passages.
- **[Dolt](https://github.com/dolthub/dolt)** — **versioned** relational storage so corpora, index artifacts, and persona prompt versions are **commit-addressable** (“what did this persona know on date X?”).

**Explicit constraint:** no embedding store, no vector ANN, no Chroma/Qdrant/pgvector (or equivalent) as part of this release.

---

## 2. Product outcome

Users can:

1. **Ingest** source documents into a **versioned** store (Dolt).
2. Build **PageIndex trees** per document or per stakeholder corpus and store pointers or JSON artifacts in Dolt.
3. **Query** with a unified `retrieve(stakeholder_id, query)` (library or thin local service) that combines PageIndex navigation and DuckDB FTS under a documented merge policy.
4. **Compose** persona prompts = static stakeholder markdown (from R1) + **cited evidence** blocks from retrieval, with logging of which nodes/snippets were used.

Open WebUI or similar is **optional packaging** only; the release is complete if retrieval + prompt assembly work from a script or minimal API.

---

## 3. Architecture (Alt B)

### 3.1 PageIndex

- Generate tree indexes from Markdown sources using PageIndex’s Markdown mode (heading hierarchy `#` / `##` / …).
- At query time, use tree search and/or PageIndex’s **agentic vectorless RAG** patterns (see upstream examples) so the model navigates **structure** rather than embedding similarity.

### 3.2 DuckDB FTS

- Relational **passage** table, e.g.:

  - `passage_id`, `stakeholder_id`, `source_uri`, `text`, `heading_path`, `created_at`, etc.

- FTS index over passage text for keywords, names, acronyms, dates.

### 3.3 Merge policy (required)

Document and implement **one** orchestration, for example:

- FTS top-k → feed titles/snippets as **hints** into PageIndex tree search, **or**
- Parallel FTS + PageIndex → **union + dedupe** by source span → token-budgeted context.

Specify **max tokens** per turn and per source.

### 3.4 Dolt

- Tables for: sources, passages, PageIndex artifact references (path or blob), rebuild metadata, persona prompt revision ids.
- **`dolt_commit`** after each meaningful ingest or prompt-template change; use branches if needed for experiments.

---

## 4. Scope

### In scope

- Ingestion pipeline: markdown (primary); other formats only if conversion to structured markdown is defined.
- Regeneration of PageIndex indexes and FTS when sources change.
- Dolt schema + documented workflow (`commit`, diff, optional `AS OF` queries).

### Out of scope (Release 3)

- Stakeholder **alignment judging**, rubric batch runs, CI score gates.

---

## 5. Deliverables checklist

| ID | Deliverable | Release criterion |
|----|-------------|-------------------|
| R2-01 | Dolt schema + ingest commits | Documented tables; each bulk ingest yields a commit; diff story documented. |
| R2-02 | Passage store + FTS | DuckDB FTS queries documented; rebuild after ingest automated or one-command. |
| R2-03 | PageIndex integration | Tree (or JSON artifact) generated per defined corpus unit; regeneration documented. |
| R2-04 | `retrieve(stakeholder_id, query)` | Returns ordered evidence with citations (doc, heading, offsets/page if available). |
| R2-05 | Persona prompt builder | Static persona + evidence section; logs selected evidence ids/paths. |
| R2-06 | Dependency manifest | **No** vector DB packages or services listed for R2. |

---

## 6. Acceptance tests

- On a fixed internal corpus, **hybrid** (PageIndex + FTS) outperforms **either alone** on a small labeled set (e.g. 20 queries with expected source headings), per metrics defined in the repo.
- Re-ingesting a transcript creates a **new Dolt commit**; historical state is queryable.
- Turning off FTS or PageIndex is a **config flag** for debugging, not a fork of the codebase.

---

## 7. Release notes (what we tell users)

**R2 delivers:** evidence-backed stakeholder replies with **no vector database**, using **PageIndex** for structured navigation, **DuckDB FTS** for lexical recall, and **Dolt** for reproducible, versioned corpora. **R1** file-based personas remain the source of static persona definitions.

---

## 8. Next release handoff

Release 3 consumes R2’s **retrieval API** and **Dolt commit ids** so judges can optionally verify proposals against **versioned evidence**. See `spec/release-3-agentic-judge.md`.
