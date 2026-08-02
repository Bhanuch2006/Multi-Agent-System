from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.graph.state import AgentState
from backend.app.tools.research import research_for_framework


@dataclass
class ResearchAgent:
    def run(self, state: AgentState) -> dict[str, Any]:
        architecture = dict(state.get("architecture", {}))
        framework = architecture.get("backend", "FastAPI")
        report = research_for_framework(framework)
        return {
            "research_notes": report.best_practices,
            "research_sources": report.references,
            "research": report.model_dump(),
        }