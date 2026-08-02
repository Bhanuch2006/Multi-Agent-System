from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os

from backend.app.graph.state import AgentState
from backend.app.models.agents import TestOutput


def _write_project(temp_dir: Path, project_files: dict[str, str]) -> None:
    for relative_path, content in project_files.items():
        target = temp_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


@dataclass
class TestingAgent:
    def run(self, state: AgentState) -> dict[str, Any]:
        project_files = dict(state.get("project_files", {}))
        tests_present = any(path.startswith("tests/") and path.endswith(".py") for path in project_files)

        with tempfile.TemporaryDirectory(prefix=f"devcrew-tests-{state.get('job_id', 'job')}-") as temp_root:
            temp_dir = Path(temp_root)
            _write_project(temp_dir, project_files)

            env = os.environ.copy()
            env.setdefault("JWT_SECRET", "dev-secret")

            if tests_present:
                result = subprocess.run(
                    [sys.executable, "-m", "pytest", "-q"],
                    cwd=temp_dir,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                passed = result.returncode == 0
                failures = [] if passed else [result.stderr.strip() or result.stdout.strip() or "pytest failed"]
                output = TestOutput(
                    passed=passed,
                    command="pytest -q",
                    stdout=result.stdout,
                    stderr=result.stderr,
                    coverage=None,
                    failures=failures,
                )
            else:
                output = TestOutput(
                    passed=False,
                    command="pytest -q",
                    stdout="",
                    stderr="No tests found in generated project.",
                    coverage=None,
                    failures=["No tests found in generated project."],
                )

        return {
            "testing": output.model_dump(),
            "messages": [{"from_agent": "Testing", "to_agent": "FixAgent", "priority": "high", "message": "; ".join(output.failures) if output.failures else "Tests passed"}],
        }
