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
        execution = dict(state.get("execution", {}))
        testing = dict(state.get("testing", {}))
        findings = review.get("findings", [])

        # Minimal heuristic fixes: if missing README -> add one; if missing passlib -> add requirement
        if "Documentation was not generated yet." in findings or "Missing README" in findings or "README.md" not in project_files:
            project_files["README.md"] = "# Project\n\nGenerated README by FixAgent."

        reqs = project_files.get("requirements.txt", "")
        if any("password" in f.lower() or "passlib" in f.lower() for f in findings) and "passlib" not in reqs:
            project_files["requirements.txt"] = reqs + "\npasslib[bcrypt]\n"

        if ".env.example" not in project_files:
            project_files[".env.example"] = "JWT_SECRET=dev-secret\nAPP_NAME=DevCrew AI\n"

        if not execution.get("passed", True):
            for error in execution.get("errors", []):
                if "ModuleNotFoundError" in error and "app" in error:
                    # keep the fix minimal: add a package marker so imports work in tests
                    project_files.setdefault("app/__init__.py", "")

        if not any(path.startswith("tests/") for path in project_files):
            project_files["tests/test_health.py"] = (
                "from fastapi.testclient import TestClient\n"
                "from app.main import app\n\n"
                "client = TestClient(app)\n\n"
                "def test_health():\n"
                "    response = client.get(\"/health\")\n"
                "    assert response.status_code == 200\n"
                "    assert response.json() == {\"status\": \"ok\"}\n"
            )

        end = perf_counter()
        end_time = datetime.utcnow()

        metrics = AgentMetrics(
            agent="FixAgent",
            start_time=start_time,
            end_time=end_time,
            tokens=0,
            cost=0.0,
            latency=end - start,
        ).model_dump(mode="json")

        return {
            "project_files": project_files,
            "revision_note": "FixAgent applied minimal fixes to affected files.",
            "metrics": metrics,
        }
