from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.graph.state import AgentState
from backend.app.models.agents import ExecutionOutput


def _write_project(temp_dir: Path, project_files: dict[str, str]) -> None:
    for relative_path, content in project_files.items():
        target = temp_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


@dataclass
class ExecutorAgent:
    def run(self, state: AgentState) -> dict[str, Any]:
        project_files = dict(state.get("project_files", {}))
        with tempfile.TemporaryDirectory(prefix=f"devcrew-{state.get('job_id', 'job')}-") as temp_root:
            temp_dir = Path(temp_root)
            _write_project(temp_dir, project_files)

            env = os.environ.copy()
            env.setdefault("JWT_SECRET", "dev-secret")

            py_files = [str(path) for path in temp_dir.rglob("*.py")]
            command = [sys.executable, "-m", "py_compile", *py_files] if py_files else [sys.executable, "-c", "print('no py files')"]
            result = subprocess.run(command, cwd=temp_dir, env=env, capture_output=True, text=True)
            errors = []
            if result.returncode != 0:
                errors.append(result.stderr.strip() or result.stdout.strip() or "py_compile failed")

            import_check = subprocess.run(
                [sys.executable, "-c", "import sys; sys.path.insert(0, '.'); import app.main"],
                cwd=temp_dir,
                env=env,
                capture_output=True,
                text=True,
            )
            if import_check.returncode != 0:
                errors.append(import_check.stderr.strip() or import_check.stdout.strip() or "import check failed")

        output = ExecutionOutput(
            passed=not errors,
            command="py_compile + import check",
            stdout=(result.stdout or "") + (import_check.stdout or ""),
            stderr=(result.stderr or "") + (import_check.stderr or ""),
            errors=errors,
        )
        return {
            "execution": output.model_dump(),
            "messages": [{"from_agent": "Executor", "to_agent": "FixAgent", "priority": "high", "message": "; ".join(errors) if errors else "Execution checks passed"}],
        }
