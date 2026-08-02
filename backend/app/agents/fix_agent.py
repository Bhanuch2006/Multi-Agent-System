from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Any

from backend.app.graph.state import AgentState
from backend.app.models.agents import AgentMetrics


class FixAgent:
    """Apply minimal fixes to affected files. Prompt: Modify only the affected files."""

    def run(self, state: AgentState) -> dict[str, Any]:
        start = perf_counter()
        start_time = datetime.utcnow()

        project_files = dict(state.get("project_files", {}))
        review = dict(state.get("review", {}))
        findings = review.get("findings", [])

        # Minimal heuristic fixes: if missing README -> add one; if missing passlib -> add requirement
        if "Documentation was not generated yet." in findings or "Missing README" in findings or "README.md" not in project_files:
            project_files["README.md"] = "# Project\n\nGenerated README by FixAgent."

        reqs = project_files.get("requirements.txt", "")
        if any("password" in f.lower() or "passlib" in f.lower() for f in findings) and "passlib" not in reqs:
            project_files["requirements.txt"] = reqs + "\npasslib[bcrypt]\n"

        end = perf_counter()
        end_time = datetime.utcnow()

        metrics = AgentMetrics(
            agent="FixAgent",
            start_time=start_time,
            end_time=end_time,
            tokens=0,
            cost=0.0,
            latency=end - start,
        ).model_dump()

        return {
            "project_files": project_files,
            "revision_note": "FixAgent applied minimal fixes to affected files.",
            "metrics": metrics,
        }
