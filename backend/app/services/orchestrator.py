from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import settings
from app.graph.state import AgentState
from app.graph.workflow import build_workflow
from app.services.project_store import create_artifact_dir, persist_artifacts, render_bundle_markdown


class Orchestrator:
    def __init__(self) -> None:
        self.workflow = build_workflow()

    def generate(self, prompt: str) -> dict[str, Any]:
        initial_state: AgentState = {
            "user_request": prompt,
            "revision_count": 0,
        }
        final_state = self.workflow.invoke(initial_state)

        project_name = str(final_state.get("project_name", "FastAPI Project"))
        project_files = dict(final_state.get("project_files", {}))
        bundle_markdown = str(final_state.get("bundle_markdown", render_bundle_markdown(project_files)))

        artifact_dir = create_artifact_dir(Path(settings.artifacts_dir), project_name)
        persisted_path = persist_artifacts(
            artifact_dir=artifact_dir,
            project_files=project_files,
            bundle_markdown=bundle_markdown,
            metadata={
                "project_name": project_name,
                "tasks": list(final_state.get("tasks", [])),
                "architecture": str(final_state.get("architecture", "")),
                "review": dict(final_state.get("review", {})),
                "revision_count": int(final_state.get("revision_count", 0)),
                "user_request": prompt,
            },
        )

        review = dict(final_state.get("review", {}))
        final_summary = str(
            final_state.get(
                "final_summary",
                f"Completed {project_name} with {int(final_state.get('revision_count', 0))} revision cycle(s).",
            )
        )

        return {
            "status": "completed",
            "project_name": project_name,
            "architecture": str(final_state.get("architecture", "")),
            "tasks": list(final_state.get("tasks", [])),
            "project_files": project_files,
            "review": {
                "verdict": str(review.get("verdict", "approved")),
                "needs_revision": bool(review.get("needs_revision", False)),
                "findings": list(review.get("findings", [])),
                "suggestions": list(review.get("suggestions", [])),
            },
            "revision_count": int(final_state.get("revision_count", 0)),
            "artifact_path": str(persisted_path),
            "bundle_markdown": bundle_markdown,
            "final_summary": final_summary,
            "metadata": {
                "supervisor_summary": str(final_state.get("supervisor_summary", "")),
            },
        }
