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


def list_artifacts(base_dir: Path) -> list[Path]:
    if not base_dir.exists():
        return []
    return [p for p in base_dir.iterdir() if p.is_dir()]


def zip_artifact(artifact_dir: Path) -> Path:
    # create a zip archive of the artifact directory
    import shutil

    base = artifact_dir.parent
    name = artifact_dir.name
    archive_path = base / f"{name}.zip"
    if archive_path.exists():
        archive_path.unlink()
    shutil.make_archive(str(base / name), "zip", root_dir=str(artifact_dir))
    return archive_path
