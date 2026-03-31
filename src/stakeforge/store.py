from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from stakeforge.dolt import DoltNotAvailable, DoltRepo
from stakeforge.duckdb_store import PassageRow, passage_id_for, upsert_passages, ensure_fts
from stakeforge.markdown_passages import read_sections
from stakeforge.pageindex_adapter import build_tree_artifact
from stakeforge.paths import StakeForgePaths
from stakeforge.runtime import StakeForgeConfig


def _dolt_enabled(cfg: StakeForgeConfig) -> bool:
    if cfg.dolt == "off":
        return False
    if cfg.dolt == "on":
        return True
    # auto
    try:
        DoltRepo(Path("."))._run(["version"], check=False)  # type: ignore[arg-type]
        return True
    except Exception:
        return False


def ingest_markdown(
    *,
    cfg: StakeForgeConfig,
    paths: StakeForgePaths,
    stakeholder_id: str,
    md_path: Path,
    source_uri: Optional[str],
    commit_message: Optional[str],
) -> None:
    """
    Ingest a markdown document for a stakeholder:
    - store raw source in Dolt (if enabled)
    - split into passages and (re)build DuckDB FTS
    - generate PageIndex artifact JSON (if enabled)
    - commit artifacts into Dolt (if enabled)
    """
    if not md_path.exists():
        raise FileNotFoundError(str(md_path))

    source_uri = source_uri or md_path.name

    # 1) Build passages + FTS (local artifact)
    sections = read_sections(md_path)
    rows: list[PassageRow] = []
    for sec in sections:
        pid = passage_id_for(stakeholder_id, source_uri, sec.heading_path, sec.text)
        rows.append(
            PassageRow(
                passage_id=pid,
                stakeholder_id=stakeholder_id,
                source_uri=source_uri,
                heading_path=sec.heading_path,
                text=sec.text,
            )
        )
    upsert_passages(paths.duckdb_path, rows)
    ensure_fts(paths.duckdb_path)

    # 2) Build PageIndex artifact (local)
    pageindex_artifact_path: Optional[Path] = None
    if cfg.use_pageindex:
        pageindex_artifact_path = (
            paths.pageindex_dir / stakeholder_id / f"{md_path.stem}.pageindex.json"
        )
        build_tree_artifact(md_path, out_json_path=pageindex_artifact_path)

    # 3) Dolt storage/commit
    if not _dolt_enabled(cfg):
        return

    repo = DoltRepo(paths.dolt_dir)
    repo.init_if_needed()
    _ensure_dolt_schema(repo)

    # copy source into dolt working tree
    rel_source = Path("sources") / stakeholder_id / md_path.name
    abs_source = repo.path / rel_source
    abs_source.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(md_path, abs_source)

    # copy artifacts into dolt working tree (commit-addressable)
    rel_duck = Path("artifacts") / "passages.duckdb"
    abs_duck = repo.path / rel_duck
    abs_duck.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(paths.duckdb_path, abs_duck)

    copied_pageindex: Optional[Path] = None
    if pageindex_artifact_path and pageindex_artifact_path.exists():
        rel_pi = Path("artifacts") / "pageindex" / stakeholder_id / pageindex_artifact_path.name
        abs_pi = repo.path / rel_pi
        abs_pi.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(pageindex_artifact_path, abs_pi)
        copied_pageindex = abs_pi

    # mirror metadata in dolt tables (so you can AS OF query without reading files)
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    repo.sql(
        f"""
        INSERT INTO sources(source_uri, stakeholder_id, path, ingested_at)
        VALUES ('{_esc(source_uri)}', '{_esc(stakeholder_id)}', '{_esc(str(rel_source))}', '{_esc(now)}')
        ON DUPLICATE KEY UPDATE
          path=VALUES(path), ingested_at=VALUES(ingested_at);
        """
    )
    if copied_pageindex:
        repo.sql(
            f"""
            INSERT INTO pageindex_artifacts(stakeholder_id, source_uri, artifact_path, created_at)
            VALUES ('{_esc(stakeholder_id)}', '{_esc(source_uri)}', '{_esc(str(copied_pageindex.relative_to(repo.path)))}', '{_esc(now)}')
            ON DUPLICATE KEY UPDATE
              artifact_path=VALUES(artifact_path), created_at=VALUES(created_at);
            """
        )
    repo.sql(
        f"""
        INSERT INTO rebuilds(stakeholder_id, source_uri, rebuilt_at, duckdb_path)
        VALUES ('{_esc(stakeholder_id)}', '{_esc(source_uri)}', '{_esc(now)}', '{_esc(str(rel_duck))}');
        """
    )

    # add/commit files + dolt table changes
    paths_to_add = [abs_source, abs_duck]
    if copied_pageindex:
        paths_to_add.append(copied_pageindex)
    repo.add(paths_to_add)

    msg = commit_message or f"ingest: {stakeholder_id} {source_uri}"
    try:
        repo.commit(msg)
    except DoltNotAvailable:
        # Shouldn't happen here (we already enabled dolt), but keep ingest resilient.
        return


def _ensure_dolt_schema(repo: DoltRepo) -> None:
    repo.sql(
        """
        CREATE TABLE IF NOT EXISTS sources (
          source_uri VARCHAR PRIMARY KEY,
          stakeholder_id VARCHAR NOT NULL,
          path VARCHAR NOT NULL,
          ingested_at VARCHAR NOT NULL
        );
        """
    )
    repo.sql(
        """
        CREATE TABLE IF NOT EXISTS pageindex_artifacts (
          stakeholder_id VARCHAR NOT NULL,
          source_uri VARCHAR NOT NULL,
          artifact_path VARCHAR NOT NULL,
          created_at VARCHAR NOT NULL,
          PRIMARY KEY (stakeholder_id, source_uri)
        );
        """
    )
    repo.sql(
        """
        CREATE TABLE IF NOT EXISTS rebuilds (
          rebuild_id INT AUTO_INCREMENT,
          stakeholder_id VARCHAR NOT NULL,
          source_uri VARCHAR NOT NULL,
          rebuilt_at VARCHAR NOT NULL,
          duckdb_path VARCHAR NOT NULL,
          PRIMARY KEY (rebuild_id)
        );
        """
    )
    repo.sql(
        """
        CREATE TABLE IF NOT EXISTS prompt_revisions (
          prompt_id VARCHAR PRIMARY KEY,
          stakeholder_id VARCHAR NOT NULL,
          created_at VARCHAR NOT NULL,
          persona_md_path VARCHAR NOT NULL,
          query VARCHAR NOT NULL,
          evidence_json_path VARCHAR NOT NULL
        );
        """
    )


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "''")

