from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, ConfigDict


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


class MdSection(BaseModel):
    model_config = ConfigDict(frozen=True)

    heading_path: str
    text: str


def split_markdown_into_sections(md_text: str) -> list[MdSection]:
    """
    Splits markdown into sections keyed by heading path.
    If there are no headings, returns a single section with empty heading_path.
    """
    lines = md_text.splitlines()
    stack: list[tuple[int, str]] = []
    sections: list[tuple[str, list[str]]] = []

    def current_path() -> str:
        return " / ".join([h for _, h in stack])

    cur_path = ""
    cur_buf: list[str] = []

    for ln in lines:
        m = _HEADING_RE.match(ln)
        if m:
            # flush existing section before starting a new one
            if cur_buf and any(s.strip() for s in cur_buf):
                sections.append((cur_path, cur_buf))
            cur_buf = []

            level = len(m.group(1))
            heading = m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, heading))
            cur_path = current_path()
            continue
        cur_buf.append(ln)

    if cur_buf and any(s.strip() for s in cur_buf):
        sections.append((cur_path, cur_buf))

    if not sections:
        return [MdSection(heading_path="", text=md_text.strip())]

    out: list[MdSection] = []
    for hp, buf in sections:
        txt = "\n".join(buf).strip()
        if not txt:
            continue
        out.append(MdSection(heading_path=hp, text=txt))
    return out


def read_sections(md_path: Path) -> list[MdSection]:
    return split_markdown_into_sections(md_path.read_text(encoding="utf-8"))

