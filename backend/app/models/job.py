from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TaskNode(BaseModel):
    id: str
    agent: str
    depends_on: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 120
    retries: int = 2


class TaskGraph(BaseModel):
    nodes: list[TaskNode] = Field(default_factory=list)


class ArtifactState(BaseModel):
    project_name: str
    project_files: dict[str, str] = Field(default_factory=dict)
    bundle_markdown: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobStateModel(BaseModel):
    job_id: str
    prompt: str
    status: str = "queued"
    current_agent: str = "Supervisor"
    progress: int = 0
    graph: TaskGraph = Field(default_factory=TaskGraph)
    completed_nodes: list[str] = Field(default_factory=list)
    failed_nodes: list[str] = Field(default_factory=list)
    skipped_nodes: list[str] = Field(default_factory=list)
    node_status: dict[str, str] = Field(default_factory=dict)
    checkpoints: int = 0
    artifact: ArtifactState | None = None
    error: str | None = None
