from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "project"


def create_artifact_dir(base_dir: Path, project_name: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    artifact_dir = base_dir / f"{slugify(project_name)}-{timestamp}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir


def render_bundle_markdown(files: dict[str, str]) -> str:
    sections: list[str] = []
    for relative_path, content in files.items():
        sections.append(f"## {relative_path}\n\n```text\n{content}\n```")
    return "\n\n".join(sections)


def write_project_files(project_dir: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        target = project_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def persist_artifacts(
    artifact_dir: Path,
    project_files: dict[str, str],
    bundle_markdown: str,
    metadata: dict[str, Any],
) -> Path:
    project_dir = artifact_dir / "project"
    project_dir.mkdir(parents=True, exist_ok=True)
    write_project_files(project_dir, project_files)
    (artifact_dir / "bundle.md").write_text(bundle_markdown, encoding="utf-8")
    (artifact_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return artifact_dir
