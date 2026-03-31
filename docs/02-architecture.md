# 02 — Architecture

## High-level system

```mermaid
flowchart LR
  You([You]) --> CLI[StakeForge CLI]
  CLI --> Artifacts[(Local DB and trees)]
  You --> LLM[Any LLM]
  CLI -. produces prompts .-> LLM
```

StakeForge is primarily a **local tool**. The LLM is outside the core; you bring your own model and API.

## Component diagram

```mermaid
flowchart TB
  CLI[stakeforge CLI]
  subgraph core [Core library]
    STORE[store.ingest_markdown]
    RET[retrieve.retrieve]
    PROMPT[prompt.build_persona_prompt]
    PERSONA[persona_load / persona_schema]
    EVAL[eval_run / eval_scorer / eval_llm_rubric]
  end
  subgraph storage [On disk]
    W[Workspace .stakeforge]
    DUCK[(passages.duckdb)]
    PI2[pageindex JSON trees]
    DOLT[(optional Dolt repo)]
  end
  CLI --> STORE
  CLI --> RET
  CLI --> PROMPT
  CLI --> EVAL
  PROMPT --> PERSONA
  STORE --> DUCK
  STORE --> PI2
  STORE --> DOLT
  RET --> DUCK
  RET --> PI2
  PROMPT --> RET
```

## Workspace layout

Default root: `.stakeforge/` (or `STAKEFORGE_ROOT`).

```mermaid
flowchart LR
  R[.stakeforge/] --> A[artifacts/passages.duckdb]
  R --> B[artifacts/pageindex/...]
  R --> C[logs/]
  R --> D[dolt/ optional]
```

| Path | Purpose |
|------|---------|
| `artifacts/passages.duckdb` | Passage rows + FTS index |
| `artifacts/pageindex/<stakeholder>/` | Tree JSON per ingested Markdown stem |
| `logs/` | `evidence.<prompt_id>.json` snapshots for each `build-prompt` |
| `dolt/` | Optional SQL-versioned copies of sources + artifacts |

## Ingest sequence

What happens when you run `stakeforge ingest`:

```mermaid
sequenceDiagram
  participant U as User
  participant CLI as stakeforge
  participant MD as Markdown file
  participant SF as split sections
  participant D as DuckDB
  participant PI as PageIndex builder
  participant DOL as Dolt optional

  U->>CLI: ingest stakeholder_id md_path
  CLI->>MD: read
  MD->>SF: heading-based passages
  SF->>D: upsert passages + rebuild FTS
  CLI->>PI: build tree JSON if enabled
  alt Dolt installed and enabled
    CLI->>DOL: copy sources + artifacts
    CLI->>DOL: commit
  end
```

## Retrieve sequence

```mermaid
sequenceDiagram
  participant U as User
  participant CLI as stakeforge
  participant R as retrieve
  participant FTS as DuckDB FTS
  participant T as PageIndex tree search
  participant M as merge and budget

  U->>CLI: retrieve query
  CLI->>R: stakeholder_id query
  par Parallel legs
    R->>FTS: top-k lexical
    R->>T: structure-aware scoring
  end
  R->>M: union dedupe token cap
  M-->>CLI: Evidence list
```

## Prompt assembly

```mermaid
flowchart TB
  subgraph inputs
    Q[User query]
    PM[Persona .md path]
    E[Evidence blocks]
  end
  subgraph prompt [Rendered prompt sections]
    R0[Reply rules + CITE format]
    R1[Stakeholder rubric from stakeforge_persona]
    R2[Static persona body]
    R3[Evidence section]
  end
  Q --> R0
  PM --> R1
  PM --> R2
  E --> R3
```

The prompt instructs the model to cite evidence as `CITE[<evidence_id>]` (see `Evidence.format_markdown()`), which powers automated evaluation.

## Evaluation pipeline

```mermaid
flowchart TB
  CASE[EvalCase JSONL]
  REP[Model reply text]
  DET[Deterministic scorer]
  LLM[Optional LLM rubric]
  OUT[EvalScores]
  CASE --> DET
  REP --> DET
  CASE --> LLM
  REP --> LLM
  DET --> OUT
  LLM --> OUT
```

When `--llm-rubric` is enabled, totals blend deterministic and rubric scores (see [06 — Evaluation](06-evaluation-and-rubric.md)).

## Configuration flags

Global CLI flags (also env-backed):

| Flag / env | Default | Effect |
|------------|---------|--------|
| `--use-fts` / `STAKEFORGE_USE_FTS` | `1` | DuckDB FTS leg in `retrieve` |
| `--use-pageindex` / `STAKEFORGE_USE_PAGEINDEX` | `1` | Tree-json leg in `retrieve` |
| `--token-budget` / `STAKEFORGE_TOKEN_BUDGET` | `1200` | Approx total evidence tokens |
| `--max-tokens-per-source` / `STAKEFORGE_MAX_TOKENS_PER_SOURCE` | `400` | Cap per `source_uri` |
| `--dolt` / `STAKEFORGE_DOLT` | `auto` | `auto` / `on` / `off` for versioned commits |

```mermaid
flowchart TD
  FTS[use_fts] --> RET2[retrieve]
  PI[use_pageindex] --> RET2
  DOL2[dolt mode] --> ING2[ingest + optional prompt log]
```

Turning off a leg is a **flag**, not a fork.

## Next document

[03 — Installation](03-installation.md)
