from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Optional

from pydantic import BaseModel, ConfigDict


class DoltNotAvailable(RuntimeError):
    pass


class DoltRepo(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: Path

    def _run(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        exe = shutil.which("dolt")
        if not exe:
            raise DoltNotAvailable("`dolt` was not found on PATH. Install Dolt to enable versioned corpora.")
        return subprocess.run(
            [exe, *args],
            cwd=str(self.path),
            check=check,
            text=True,
            capture_output=True,
        )

    def init_if_needed(self) -> None:
        if (self.path / ".dolt").exists():
            return
        self.path.mkdir(parents=True, exist_ok=True)
        self._run(["init"])

    def sql(self, query: str) -> str:
        cp = self._run(["sql", "-q", query])
        return cp.stdout

    def add(self, paths: Iterable[Path]) -> None:
        rels: list[str] = []
        for p in paths:
            try:
                rels.append(str(p.relative_to(self.path)))
            except ValueError:
                raise ValueError(f"Path {p} is not inside Dolt repo {self.path}")
        if not rels:
            return
        self._run(["add", *rels])

    def commit(self, message: str) -> str:
        cp = self._run(["commit", "-m", message], check=False)
        # dolt returns exit 1 if nothing to commit
        return cp.stdout + cp.stderr

    def status(self) -> str:
        cp = self._run(["status"], check=False)
        return cp.stdout + cp.stderr

    def current_commit(self) -> Optional[str]:
        cp = self._run(["log", "-n", "1", "--pretty=oneline"], check=False)
        line = (cp.stdout or "").strip().splitlines()
        if not line:
            return None
        return line[0].split(" ", 1)[0]

