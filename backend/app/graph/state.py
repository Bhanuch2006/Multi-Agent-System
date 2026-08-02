from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    user_request: str
    project_name: str
    task_list: list[str]
    architecture: dict[str, Any]
    research_notes: list[str]
    research_sources: list[str]
    project_files: dict[str, str]
    review: dict[str, Any]
    documentation: str
    revision_count: int
    artifact_path: str
    bundle_markdown: str
    final_summary: str
    supervisor_summary: str
    architect_summary: str
    research_summary: str
    coding_summary: str
    documentation_summary: str
    current_agent: str
    progress: int
    status: str
    messages: list[dict]
    metrics: list[dict]
