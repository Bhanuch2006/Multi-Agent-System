from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)


class ArchitecturePlan(BaseModel):
    backend: str
    database: str
    authentication: str
    orm: str
    pattern: str
    folder_structure: str
    notes: list[str] = Field(default_factory=list)


class ResearchReport(BaseModel):
    notes: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class ReviewReport(BaseModel):
    verdict: str
    needs_revision: bool
    overall_score: int = 0
    category_scores: dict[str, int] = Field(default_factory=dict)
    findings: list[str]
    suggestions: list[str]


class GenerateResult(BaseModel):
    status: str
    project_name: str
    task_list: list[str]
    architecture: ArchitecturePlan
    research: ResearchReport
    project_files: dict[str, str]
    review: ReviewReport
    execution: dict[str, Any] = Field(default_factory=dict)
    testing: dict[str, Any] = Field(default_factory=dict)
    documentation: str
    revision_count: int
    artifact_path: str | None = None
    bundle_markdown: str
    final_summary: str
    graph: dict[str, Any] = Field(default_factory=dict)
    node_status: dict[str, str] = Field(default_factory=dict)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    metrics: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GenerateJobResponse(BaseModel):
    job_id: str
    status: str
    current_agent: str
    progress: int


class JobStatusResponse(GenerateJobResponse):
    result: GenerateResult | None = None
    error: str | None = None
