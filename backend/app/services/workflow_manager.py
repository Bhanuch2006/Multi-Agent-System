from __future__ import annotations

import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.app.agents.architect import ArchitectAgent
from backend.app.agents.coder import CoderAgent
from backend.app.agents.documentation import DocumentationAgent
from backend.app.agents.executor import ExecutorAgent
from backend.app.agents.fix_agent import FixAgent
from backend.app.agents.researcher import ResearchAgent
from backend.app.agents.reviewer import ReviewerAgent
from backend.app.agents.testing import TestingAgent
from backend.app.agents.supervisor import SupervisorAgent
from backend.app.core.config import settings
from backend.app.models.response import ArchitecturePlan, GenerateResult, ResearchReport, ReviewReport
from backend.app.services.checkpoint_store import checkpoint_store
from backend.app.services.event_bus import bus
from backend.app.services.job_store import job_store
from backend.app.services.memory_store import memory_store
from backend.app.services.model_router import model_router
from backend.app.services.planner import planner
from backend.app.services.project_store import create_artifact_dir, persist_artifacts, render_bundle_markdown


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobState:
    job_id: str
    prompt: str
    graph: dict[str, Any]
    state: dict[str, Any] = field(default_factory=dict)
    node_status: dict[str, str] = field(default_factory=dict)
    node_attempts: dict[str, int] = field(default_factory=dict)
    running: dict[str, dict[str, Any]] = field(default_factory=dict)
    completed_nodes: list[str] = field(default_factory=list)
    skipped_nodes: list[str] = field(default_factory=list)
    failed_nodes: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)


class WorkflowManager:
    """Schedules jobs, publishes events, checkpoints state, and retries through FixAgent."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=8)
        self._jobs: dict[str, JobState] = {}
        self._lock = threading.Lock()

    def start_job(self, prompt: str) -> str:
        record = job_store.create(prompt)
        supervisor_state = SupervisorAgent().run({"user_request": prompt})
        graph = planner.plan(prompt)

        initial_state: dict[str, Any] = {
            "job_id": record.job_id,
            "user_request": prompt,
            "project_name": supervisor_state.get("project_name", "FastAPI Project"),
            "architecture": supervisor_state.get("architecture", {}),
            "task_list": supervisor_state.get("task_list", []),
            "project_files": {},
            "review": {},
            "execution": {},
            "testing": {},
            "documentation": "",
            "revision_count": 0,
            "artifact_path": "",
            "bundle_markdown": "",
            "final_summary": "",
            "messages": [],
            "metrics": [],
            "graph": graph,
            "node_status": {node["id"]: "pending" for node in graph.get("nodes", [])},
            "current_agent": "Supervisor",
            "progress": 0,
            "status": "running",
        }

        job_state = JobState(
            job_id=record.job_id,
            prompt=prompt,
            graph=graph,
            state=initial_state,
            node_status=dict(initial_state["node_status"]),
        )
        self._jobs[record.job_id] = job_state

        job_store.update(
            record.job_id,
            status="running",
            current_agent="Planner",
            progress=5,
            graph=graph,
            node_status=dict(job_state.node_status),
        )
        bus.publish("job.created", {"job_id": record.job_id, "prompt": prompt, "graph": graph})
        checkpoint_store.append(record.job_id, "job.created", {"prompt": prompt, "graph": graph}, state=initial_state)

        worker = threading.Thread(target=self._run_scheduler, args=(record.job_id,), daemon=True)
        worker.start()
        return record.job_id

    def get_job(self, job_id: str) -> JobState | None:
        return self._jobs.get(job_id)

    def _run_scheduler(self, job_id: str) -> None:
        state = self._jobs[job_id]
        nodes = {node["id"]: node for node in state.graph.get("nodes", [])}
        while True:
            self._dispatch_ready_nodes(state, nodes)
            self._process_running_nodes(state, nodes)
            self._maybe_run_fix(state, nodes)

            if self._is_work_complete(state, nodes):
                self._finalize_job(state)
                return

            time.sleep(0.2)

    def _dispatch_ready_nodes(self, state: JobState, nodes: dict[str, dict[str, Any]]) -> None:
        for node_id, spec in nodes.items():
            if state.node_status.get(node_id) != "pending":
                continue
            if not self._dependencies_ready(state, spec):
                continue
            if not self._condition_ready(state, spec):
                # mark nodes that should never run on this branch as skipped
                if self._condition_terminal(state, spec):
                    state.node_status[node_id] = "skipped"
                    state.skipped_nodes.append(node_id)
                    checkpoint_store.append(state.job_id, f"{node_id}.skipped", {"node": node_id}, state=state.state)
                continue

            self._start_node(state, node_id, spec)

    def _start_node(self, state: JobState, node_id: str, spec: dict[str, Any]) -> None:
        agent_name = node_id
        task_hint = spec.get("metadata", {}).get("task_hint", node_id)
        model_name = model_router.resolve(agent_name, task_hint).model

        state.node_status[node_id] = "running"
        state.state["current_agent"] = node_id.title()
        state.state["node_id"] = node_id
        state.state["task_hint"] = task_hint
        state.state["model"] = model_name
        state.node_attempts[node_id] = state.node_attempts.get(node_id, 0) + 1
        job_store.update(
            state.job_id,
            current_agent=node_id.title(),
            progress=self._progress(state),
            node_status=dict(state.node_status),
            graph=state.graph,
        )

        bus.publish("task.started", {"job_id": state.job_id, "node": node_id, "model": model_name})
        checkpoint_store.append(
            state.job_id,
            "task.started",
            {"node": node_id, "model": model_name, "attempt": state.node_attempts[node_id]},
            state=state.state,
        )

        future = self._executor.submit(self._execute_node, state.job_id, node_id, task_hint, model_name)
        state.running[node_id] = {
            "future": future,
            "started_at": time.time(),
            "timeout": spec.get("timeout_seconds", settings.node_timeout_seconds),
        }

    def _process_running_nodes(self, state: JobState, nodes: dict[str, dict[str, Any]]) -> None:
        finished: list[str] = []
        for node_id, run_info in state.running.items():
            future: Future = run_info["future"]
            timeout = float(run_info["timeout"])
            started_at = float(run_info["started_at"])
            if future.done():
                try:
                    result = future.result()
                    self._apply_result(state, node_id, result)
                except Exception as exc:  # pragma: no cover - surfaced through status endpoint
                    self._handle_failure(state, node_id, str(exc))
                finished.append(node_id)
                continue

            if time.time() - started_at > timeout:
                self._handle_failure(state, node_id, f"Timeout after {timeout} seconds")
                finished.append(node_id)

        for node_id in finished:
            state.running.pop(node_id, None)

    def _maybe_run_fix(self, state: JobState, nodes: dict[str, dict[str, Any]]) -> None:
        if not state.state.get("needs_fix"):
            return
        if state.state.get("fix_running"):
            return
        if int(state.state.get("revision_count", 0)) >= settings.max_revision_cycles:
            for node_id, spec in nodes.items():
                if state.node_status.get(node_id) == "pending" and self._condition_terminal(state, spec):
                    state.node_status[node_id] = "skipped"
                    state.skipped_nodes.append(node_id)
            state.state["needs_fix"] = False
            job_store.update(state.job_id, node_status=dict(state.node_status), progress=self._progress(state))
            return
        # run fix synchronously in the scheduler thread so we can immediately reschedule downstream steps
        state.state["fix_running"] = True
        try:
            fix_result = FixAgent().run(state.state)
            for key, value in fix_result.items():
                if key not in {"project_files", "messages", "metrics"}:
                    state.state[key] = value
            if fix_result.get("project_files"):
                project_files = dict(state.state.get("project_files", {}))
                project_files.update(dict(fix_result.get("project_files", {})))
                state.state["project_files"] = project_files
            if fix_result.get("messages"):
                messages = list(state.state.get("messages", []))
                messages.extend(fix_result.get("messages", []))
                state.state["messages"] = messages
            if fix_result.get("metrics"):
                metrics = list(state.state.get("metrics", []))
                metrics.append(fix_result.get("metrics"))
                state.state["metrics"] = metrics
            state.state["revision_count"] = int(state.state.get("revision_count", 0)) + 1
            state.state["needs_fix"] = False
            state.state["fix_running"] = False
            state.node_status["fix"] = "completed"
            bus.publish("fix.completed", {"job_id": state.job_id, "revision_count": state.state["revision_count"]})
            checkpoint_store.append(state.job_id, "fix.completed", fix_result, state=state.state)

            # rerun validation/review after a fix so the job converges on a verified artifact
            for node_id in ("executor", "testing", "reviewer", "documentation"):
                if node_id in state.node_status:
                    state.node_status[node_id] = "pending"
            state.running.clear()
            job_store.update(state.job_id, node_status=dict(state.node_status), progress=self._progress(state), current_agent="FixAgent")
        except Exception as exc:  # pragma: no cover - surfaced through status endpoint
            state.state["fix_running"] = False
            self._handle_failure(state, "fix", str(exc))

    def _execute_node(self, job_id: str, node_id: str, task_hint: str, model_name: str) -> dict[str, Any]:
        state = self._jobs[job_id].state
        state = {**state, "node_id": node_id, "task_hint": task_hint, "model": model_name}
        agent_map = {
            "research": ResearchAgent,
            "architect": ArchitectAgent,
            "database": CoderAgent,
            "auth": CoderAgent,
            "crud": CoderAgent,
            "frontend": CoderAgent,
            "docker": CoderAgent,
            "ci": CoderAgent,
            "executor": ExecutorAgent,
            "testing": TestingAgent,
            "reviewer": ReviewerAgent,
            "documentation": DocumentationAgent,
        }
        AgentCls = agent_map.get(node_id, CoderAgent)
        agent = AgentCls()
        return agent.run(state)

    def _apply_result(self, state: JobState, node_id: str, result: dict[str, Any]) -> None:
        state.node_status[node_id] = "completed"
        state.completed_nodes.append(node_id)
        for key, value in result.items():
            if key not in {"project_files", "messages", "metrics", "review", "execution", "testing"}:
                state.state[key] = value

        if result.get("project_files"):
            project_files = dict(state.state.get("project_files", {}))
            project_files.update(dict(result.get("project_files", {})))
            state.state["project_files"] = project_files

        if result.get("messages"):
            messages = list(state.state.get("messages", []))
            messages.extend(result.get("messages", []))
            state.state["messages"] = messages

        if result.get("metrics"):
            metrics = list(state.state.get("metrics", []))
            metrics.append(result.get("metrics"))
            state.state["metrics"] = metrics

        if result.get("review"):
            state.state["review"] = result.get("review", {})

        if result.get("execution"):
            state.state["execution"] = result.get("execution", {})
            if not result["execution"].get("passed", True):
                state.state["needs_fix"] = True

        if result.get("testing"):
            state.state["testing"] = result.get("testing", {})
            if not result["testing"].get("passed", True):
                state.state["needs_fix"] = True

        if node_id == "reviewer":
            review = dict(state.state.get("review", {}))
            if not review.get("approved", False):
                state.state["needs_fix"] = True
                if int(state.state.get("revision_count", 0)) >= settings.max_revision_cycles:
                    state.state["final_revision_exhausted"] = True

        if node_id == "documentation":
            state.state["documentation"] = str(result.get("documentation", state.state.get("documentation", "")))

        checkpoint_store.append(state.job_id, f"{node_id}.completed", result, state=state.state)
        bus.publish(f"{node_id}.completed", {"job_id": state.job_id, "node": node_id, "result": result})
        job_store.update(
            state.job_id,
            current_agent=node_id.title(),
            progress=self._progress(state),
            node_status=dict(state.node_status),
        )

    def _handle_failure(self, state: JobState, node_id: str, error: str) -> None:
        state.node_status[node_id] = "failed"
        state.failed_nodes.append(node_id)
        state.state["needs_fix"] = True
        state.state["last_failure"] = {"node": node_id, "error": error}
        checkpoint_store.append(state.job_id, f"{node_id}.failed", {"error": error}, state=state.state)
        bus.publish(f"{node_id}.failed", {"job_id": state.job_id, "node": node_id, "error": error})
        job_store.update(
            state.job_id,
            current_agent="FixAgent",
            progress=self._progress(state),
            node_status=dict(state.node_status),
            error=error,
        )

    def _dependencies_ready(self, state: JobState, spec: dict[str, Any]) -> bool:
        dependencies = spec.get("depends_on", []) or []
        return all(state.node_status.get(dep) == "completed" for dep in dependencies)

    def _condition_ready(self, state: JobState, spec: dict[str, Any]) -> bool:
        metadata = spec.get("metadata", {}) or {}
        when = metadata.get("when")
        if when is None:
            return True
        review = dict(state.state.get("review", {}))
        approved = bool(review.get("approved", False))
        if when == "review_approved":
            return approved or bool(state.state.get("final_revision_exhausted"))
        if when == "review_failed":
            return not approved and bool(review)
        return True

    def _condition_terminal(self, state: JobState, spec: dict[str, Any]) -> bool:
        metadata = spec.get("metadata", {}) or {}
        when = metadata.get("when")
        review = dict(state.state.get("review", {}))
        approved = bool(review.get("approved", False))
        if when == "review_approved" and not approved and state.state.get("final_revision_exhausted"):
            return True
        if when == "review_failed" and approved and review:
            return True
        return False

    def _is_work_complete(self, state: JobState, nodes: dict[str, dict[str, Any]]) -> bool:
        if state.running:
            return False
        terminal_status = {"completed", "skipped"}
        return all(status in terminal_status for status in state.node_status.values()) and bool(state.node_status)

    def _progress(self, state: JobState) -> int:
        total = max(len(state.node_status), 1)
        completed = sum(1 for status in state.node_status.values() if status == "completed")
        return min(99, int((completed / total) * 100))

    def _finalize_job(self, state: JobState) -> None:
        project_name = str(state.state.get("project_name", "FastAPI Project"))
        project_files = dict(state.state.get("project_files", {}))
        bundle_markdown = render_bundle_markdown(project_files)
        state.state["bundle_markdown"] = bundle_markdown

        artifact_dir = create_artifact_dir(Path(settings.artifacts_dir), project_name)
        persisted_path = persist_artifacts(
            artifact_dir=artifact_dir,
            project_files=project_files,
            bundle_markdown=bundle_markdown,
            metadata={
                "project_name": project_name,
                "task_list": list(state.state.get("task_list", [])),
                "architecture": dict(state.state.get("architecture", {})),
                "research_notes": list(state.state.get("research_notes", [])),
                "research_sources": list(state.state.get("research_sources", [])),
                "review": dict(state.state.get("review", {})),
                "execution": dict(state.state.get("execution", {})),
                "testing": dict(state.state.get("testing", {})),
                "revision_count": int(state.state.get("revision_count", 0)),
                "user_request": state.prompt,
                "messages": list(state.state.get("messages", [])),
                "metrics": list(state.state.get("metrics", [])),
                "graph": state.graph,
                "node_status": dict(state.node_status),
                "checkpoints": len(checkpoint_store.read(state.job_id)),
            },
        )

        review = dict(state.state.get("review", {}))
        review_report = ReviewReport.model_validate(
            {
                "verdict": "approved" if review.get("approved", False) else "needs_revision",
                "needs_revision": not bool(review.get("approved", False)),
                "overall_score": int(review.get("overall_score", review.get("score", 0)) or 0),
                "category_scores": dict(review.get("category_scores", {})),
                "findings": list(review.get("findings", [])),
                "suggestions": list(review.get("suggestions", [])),
            }
        )

        result = GenerateResult(
            status="completed",
            project_name=project_name,
            task_list=list(state.state.get("task_list", [])),
            architecture=ArchitecturePlan.model_validate(state.state.get("architecture", {})),
            research=ResearchReport(
                notes=list(state.state.get("research_notes", [])),
                sources=list(state.state.get("research_sources", [])),
            ),
            project_files=project_files,
            review=review_report,
            execution=dict(state.state.get("execution", {})),
            testing=dict(state.state.get("testing", {})),
            documentation=str(state.state.get("documentation", "")),
            revision_count=int(state.state.get("revision_count", 0)),
            artifact_path=str(persisted_path),
            bundle_markdown=bundle_markdown,
            final_summary=str(state.state.get("final_summary", "Completed workflow.")),
            graph=state.graph,
            node_status=dict(state.node_status),
            messages=list(state.state.get("messages", [])),
            metrics=list(state.state.get("metrics", [])),
            metadata={
                "graph": state.graph,
                "node_status": dict(state.node_status),
                "messages": list(state.state.get("messages", [])),
                "metrics": list(state.state.get("metrics", [])),
                "execution": dict(state.state.get("execution", {})),
                "testing": dict(state.state.get("testing", {})),
            },
        )

        memory_store.remember(
            prompt=state.prompt,
            lessons=[
                f"Reviewed {project_name} with {len(project_files)} files.",
                f"Final review score: {review_report.overall_score}.",
            ],
            preferences=[str(state.state.get("project_name", "FastAPI Project"))],
            failures=list(review_report.findings),
            successes=["Workflow completed successfully."],
        )

        checkpoint_store.append(state.job_id, "artifact.generated", {"artifact_path": str(persisted_path)}, state=state.state)
        bus.publish("artifact.generated", {"job_id": state.job_id, "artifact_path": str(persisted_path)})
        bus.publish("job.completed", {"job_id": state.job_id, "artifact_path": str(persisted_path)})

        state.state["artifact_path"] = str(persisted_path)
        state.state["result"] = result.model_dump()
        state.state["status"] = "completed"
        state.state["current_agent"] = "Documentation"
        job_store.complete(state.job_id, result.model_dump())


# single manager instance
manager = WorkflowManager()
