from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    user_request: str
    project_name: str
    architecture: str
    tasks: list[str]
    project_files: dict[str, str]
    review: dict[str, Any]
    revision_count: int
    artifact_path: str
    bundle_markdown: str
    final_summary: str
    supervisor_summary: str
