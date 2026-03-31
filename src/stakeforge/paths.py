from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class StakeForgePaths(BaseModel):
    model_config = ConfigDict(frozen=True)

    root: Path

    @property
    def dolt_dir(self) -> Path:
        return self.root / "dolt"

    @property
    def artifacts_dir(self) -> Path:
        return self.root / "artifacts"

    @property
    def pageindex_dir(self) -> Path:
        return self.artifacts_dir / "pageindex"

    @property
    def duckdb_path(self) -> Path:
        return self.artifacts_dir / "passages.duckdb"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    def ensure_dirs(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.pageindex_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

