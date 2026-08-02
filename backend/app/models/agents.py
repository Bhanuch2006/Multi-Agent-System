from __future__ import annotations

from datetime import datetime
from typing import Any, List

from pydantic import BaseModel


class ReviewOutput(BaseModel):
    score: int
    approved: bool
    findings: List[str]
    suggestions: List[str]


class ResearchOutput(BaseModel):
    framework: str
    best_practices: List[str]
    references: List[str]


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
