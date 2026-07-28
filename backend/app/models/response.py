from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)


class ReviewReport(BaseModel):
    verdict: str
    needs_revision: bool
    findings: list[str]
    suggestions: list[str]


class GenerateResponse(BaseModel):
    status: str
    project_name: str
    architecture: str
    tasks: list[str]
    project_files: dict[str, str]
    review: ReviewReport
    revision_count: int
    artifact_path: str | None = None
    bundle_markdown: str
    final_summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)
