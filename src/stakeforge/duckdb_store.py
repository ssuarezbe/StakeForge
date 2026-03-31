from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, Optional

import duckdb
from pydantic import BaseModel, ConfigDict


class PassageRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    passage_id: str
    stakeholder_id: str
    source_uri: str
    heading_path: str
    text: str


def _stable_id(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x1f")
    return h.hexdigest()[:20]


def ensure_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS passages (
              passage_id VARCHAR PRIMARY KEY,
              stakeholder_id VARCHAR NOT NULL,
              source_uri VARCHAR NOT NULL,
              heading_path VARCHAR,
              text VARCHAR NOT NULL,
              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    finally:
        con.close()


def upsert_passages(db_path: Path, rows: Iterable[PassageRow]) -> int:
    ensure_schema(db_path)
    con = duckdb.connect(str(db_path))
    try:
        inserted = 0
        for r in rows:
            con.execute(
                """
                INSERT OR REPLACE INTO passages(passage_id, stakeholder_id, source_uri, heading_path, text)
                VALUES (?, ?, ?, ?, ?)
                """,
                [r.passage_id, r.stakeholder_id, r.source_uri, r.heading_path, r.text],
            )
            inserted += 1
        return inserted
    finally:
        con.close()


def ensure_fts(db_path: Path) -> None:
    ensure_schema(db_path)
    con = duckdb.connect(str(db_path))
    try:
        try:
            con.execute("INSTALL fts;")
        except Exception:
            pass
        con.execute("LOAD fts;")

        # DuckDB's FTS is PRAGMA-driven (e.g. create_fts_index). Calling it
        # repeatedly may throw if the index already exists; in that case we
        # just verify the expected FTS relation exists and continue.
        try:
            con.execute("PRAGMA create_fts_index('passages', 'passage_id', 'text');")
        except Exception as e:
            # If the index already exists, DuckDB throws. It's safe to ignore
            # because the underlying index should already be usable for queries.
            msg = str(e).lower()
            if "fts index already exists" in msg or "already exists on table" in msg:
                return
            raise
    finally:
        con.close()


def search_fts(
    db_path: Path,
    *,
    stakeholder_id: str,
    query: str,
    top_k: int = 8,
) -> list[dict]:
    ensure_fts(db_path)
    con = duckdb.connect(str(db_path))
    try:
        res = con.execute(
            """
            WITH scored AS (
              SELECT
                p.passage_id,
                p.stakeholder_id,
                p.source_uri,
                COALESCE(p.heading_path, '') AS heading_path,
                p.text,
                fts_main_passages.match_bm25(p.passage_id, ?) AS score
              FROM passages p
              WHERE p.stakeholder_id = ?
            )
            SELECT
              passage_id,
              stakeholder_id,
              source_uri,
              heading_path,
              text,
              score
            FROM scored
            WHERE score IS NOT NULL
            ORDER BY score DESC
            LIMIT ?
            """,
            [query, stakeholder_id, top_k],
        ).fetchall()
        cols = ["passage_id", "stakeholder_id", "source_uri", "heading_path", "text", "score"]
        return [dict(zip(cols, row)) for row in res]
    finally:
        con.close()


def passage_id_for(stakeholder_id: str, source_uri: str, heading_path: str, text: str) -> str:
    return _stable_id(stakeholder_id, source_uri, heading_path, text)

