from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from backend.app.services.event_bus import bus
from backend.app.services.event_store import store
from backend.app.services.planner import planner
from backend.app.services.job_store import job_store

from backend.app.agents.researcher import ResearchAgent
from backend.app.agents.coder import CoderAgent
from backend.app.agents.reviewer import ReviewerAgent
from backend.app.agents.fix_agent import FixAgent
from backend.app.agents.documentation import DocumentationAgent
from backend.app.agents.architect import ArchitectAgent


@dataclass
class JobState:
    job_id: str
    prompt: str
    graph: dict[str, Any]
    completed: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WorkflowManager:
    """Schedules tasks based on dependency graph and coordinates via EventBus.

    This is intentionally simple: nodes map to agent workers by name.
    """

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._jobs: Dict[str, JobState] = {}
        # subscribe to events for replay/persistence
        bus.subscribe("*.completed", self._on_task_completed)

    def start_job(self, prompt: str) -> str:
        # create a job and plan a DAG
        record = job_store.create(prompt)
        graph = planner.plan(prompt)
        job_state = JobState(job_id=record.job_id, prompt=prompt, graph=graph)
        self._jobs[record.job_id] = job_state

        # publish planner finished
        ev = {"job_id": record.job_id, "graph": graph}
        store.append(record.job_id, {"event": "planner.finished", "payload": ev})
        bus.publish("planner.finished", ev)

        # schedule runner thread
        t = threading.Thread(target=self._run_scheduler, args=(record.job_id,), daemon=True)
        t.start()
        return record.job_id

    def _run_scheduler(self, job_id: str) -> None:
        state = self._jobs[job_id]
        nodes = {n["id"]: n for n in state.graph.get("nodes", [])}

        # simple loop: find runnable nodes (dependencies satisfied), submit them
        while True:
            runnable = []
            for nid, spec in nodes.items():
                if nid in state.completed or nid in state.failed:
                    continue
                deps = spec.get("depends_on", []) or []
                if all(d in state.completed for d in deps):
                    runnable.append(nid)

            if not runnable:
                # finished if all nodes completed
                if all(n in state.completed or n in state.failed for n in nodes):
                    bus.publish("job.completed", {"job_id": job_id})
                    store.append(job_id, {"event": "job.completed", "payload": {"job_id": job_id}})
                    job_store.complete(job_id, {})
                    return
                # wait for events
                time.sleep(0.5)
                continue

            # submit runnable nodes
            for nid in runnable:
                self._executor.submit(self._execute_node, job_id, nid)
                # mark as running to avoid duplicate submission
                state.completed.append(nid)  # optimistic mark; will be idempotent
                store.append(job_id, {"event": "task.started", "payload": {"job_id": job_id, "node": nid}})
                bus.publish(f"task.started", {"job_id": job_id, "node": nid})

    def _execute_node(self, job_id: str, node_id: str) -> None:
        # dispatch to agent worker
        try:
            agent_map = {
                "research": ResearchAgent,
                "coder": CoderAgent,
                "reviewer": ReviewerAgent,
                "fix_agent": FixAgent,
                "documentation": DocumentationAgent,
                "architect": ArchitectAgent,
                "database": CoderAgent,
                "auth": CoderAgent,
                "crud": CoderAgent,
                "tests": CoderAgent,
            }
            AgentCls = agent_map.get(node_id, CoderAgent)
            agent = AgentCls()
            # minimal state passed
            result = agent.run({"job_id": job_id, "node_id": node_id})
            payload = {"job_id": job_id, "node": node_id, "result": result}
            store.append(job_id, {"event": f"{node_id}.completed", "payload": payload})
            bus.publish(f"{node_id}.completed", payload)
        except Exception as exc:
            store.append(job_id, {"event": f"{node_id}.failed", "payload": {"error": str(exc)}})
            bus.publish(f"{node_id}.failed", {"job_id": job_id, "node": node_id, "error": str(exc)})

    def _on_task_completed(self, event: dict[str, Any]) -> None:
        # when tasks complete, mark them in job state
        payload = event.get("payload", {})
        job_id = payload.get("job_id")
        node = payload.get("node")
        if not job_id or not node:
            return
        state = self._jobs.get(job_id)
        if not state:
            return
        # mark completed (if not already)
        if node not in state.completed:
            state.completed.append(node)


# single manager instance
manager = WorkflowManager()
