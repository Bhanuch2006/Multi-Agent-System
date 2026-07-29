from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from backend.app.core.config import settings
from backend.app.graph.state import AgentState
from backend.app.graph.workflow import build_workflow
from backend.app.models.response import ArchitecturePlan, GenerateResult, ResearchReport, ReviewReport
from backend.app.services.job_store import job_store
from backend.app.services.project_store import create_artifact_dir, persist_artifacts, render_bundle_markdown


class Orchestrator:
    def __init__(self) -> None:
        self.workflow = build_workflow()

    def submit(self, prompt: str) -> dict[str, Any]:
        record = job_store.create(prompt)
        worker = threading.Thread(target=self._run_job, args=(record.job_id, prompt), daemon=True)
        worker.start()
        return self.get_status(record.job_id) or {"job_id": record.job_id, "status": record.status, "current_agent": record.current_agent, "progress": record.progress}

    def get_status(self, job_id: str) -> dict[str, Any] | None:
        record = job_store.get(job_id)
        if not record:
            return None
        payload: dict[str, Any] = {
            "job_id": record.job_id,
            "status": record.status,
            "current_agent": record.current_agent,
            "progress": record.progress,
            "error": record.error,
            "result": record.result,
        }
        return payload

    def _run_job(self, job_id: str, prompt: str) -> None:
        try:
            initial_state: AgentState = {
                "user_request": prompt,
                "revision_count": 0,
                "status": "running",
                "current_agent": "Supervisor",
                "progress": 0,
            }

            state = initial_state
            for update in self.workflow.stream(initial_state):
                node_name, node_state = next(iter(update.items()))
                state = {**state, **node_state}
                progress = int(node_state.get("progress", state.get("progress", 0)))
                current_agent = str(node_state.get("current_agent", node_name.title()))
                job_store.update(job_id, current_agent=current_agent, progress=progress, status=str(node_state.get("status", "running")))

            project_name = str(state.get("project_name", "FastAPI Project"))
            project_files = dict(state.get("project_files", {}))
            bundle_markdown = str(state.get("bundle_markdown", render_bundle_markdown(project_files)))

            artifact_dir = create_artifact_dir(Path(settings.artifacts_dir), project_name)
            persisted_path = persist_artifacts(
                artifact_dir=artifact_dir,
                project_files=project_files,
                bundle_markdown=bundle_markdown,
                metadata={
                    "project_name": project_name,
                    "task_list": list(state.get("task_list", [])),
                    "architecture": dict(state.get("architecture", {})),
                    "research_notes": list(state.get("research_notes", [])),
                    "research_sources": list(state.get("research_sources", [])),
                    "review": dict(state.get("review", {})),
                    "revision_count": int(state.get("revision_count", 0)),
                    "user_request": prompt,
                },
            )

            review = dict(state.get("review", {}))
            final_result = GenerateResult(
                status="completed",
                project_name=project_name,
                task_list=list(state.get("task_list", [])),
                architecture=ArchitecturePlan.model_validate(state.get("architecture", {})),
                research=ResearchReport(
                    notes=list(state.get("research_notes", [])),
                    sources=list(state.get("research_sources", [])),
                ),
                project_files=project_files,
                review=ReviewReport.model_validate(
                    {
                        "verdict": str(review.get("verdict", "approved")),
                        "needs_revision": bool(review.get("needs_revision", False)),
                        "findings": list(review.get("findings", [])),
                        "suggestions": list(review.get("suggestions", [])),
                    }
                ),
                documentation=str(state.get("documentation", "")),
                revision_count=int(state.get("revision_count", 0)),
                artifact_path=str(persisted_path),
                bundle_markdown=bundle_markdown,
                final_summary=str(state.get("final_summary", "")),
                metadata={
                    "supervisor_summary": str(state.get("supervisor_summary", "")),
                    "architect_summary": str(state.get("architect_summary", "")),
                    "research_summary": str(state.get("research_summary", "")),
                    "coding_summary": str(state.get("coding_summary", "")),
                    "documentation_summary": str(state.get("documentation_summary", "")),
                },
            )

            job_store.complete(job_id, final_result.model_dump())
        except Exception as exc:  # pragma: no cover - surfaced through status endpoint
            job_store.fail(job_id, str(exc))
