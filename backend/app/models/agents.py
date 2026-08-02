from __future__ import annotations

from datetime import datetime
from typing import Any, List

from pydantic import BaseModel, ConfigDict, Field


class ReviewOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    overall_score: int = Field(alias="score")
    approved: bool
    category_scores: dict[str, int]
    findings: List[str]
    suggestions: List[str]


class ResearchOutput(BaseModel):
    framework: str
    best_practices: List[str]
    references: List[str]


class ExecutionOutput(BaseModel):
    passed: bool
    command: str
    stdout: str = ""
    stderr: str = ""
    errors: List[str] = []


class TestOutput(BaseModel):
    passed: bool
    command: str
    stdout: str = ""
    stderr: str = ""
    coverage: float | None = None
    failures: List[str] = []


class CodeFile(BaseModel):
    path: str
    content: str


class AgentMessage(BaseModel):
    from_agent: str
    to_agent: str
    priority: str
    message: str
    timestamp: datetime | None = None


class AgentMetrics(BaseModel):
    agent: str
    start_time: datetime
    end_time: datetime
    tokens: int = 0
    cost: float = 0.0
    latency: float | None = None
