from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any


def _has_any(prompt: str, keywords: tuple[str, ...]) -> bool:
    lowered = prompt.lower()
    return any(keyword in lowered for keyword in keywords)


@dataclass
class NodeSpec:
    id: str
    depends_on: List[str]
    metadata: Dict[str, Any] | None = None


class Planner:
    """Produce a dependency graph (DAG) from a prompt or supervisor output.

    This is a simple, rule-based planner for now. In the future it can call
    an LLM supervisor to produce a rich DAG.
    """

    def plan(self, prompt: str) -> dict[str, List[dict]]:
        lowered = prompt.lower()
        backend_only = _has_any(lowered, ("backend only", "backend-only", "backend only.", "only backend"))
        wants_frontend = _has_any(lowered, ("frontend", "react", "nextjs", "next.js", "ui", "web app")) and not backend_only
        wants_docker = _has_any(lowered, ("docker", "container", "dockerfile"))
        wants_ci = _has_any(lowered, ("ci", "github actions", "workflow", "pipeline"))
        wants_auth = _has_any(lowered, ("auth", "jwt", "login", "signup", "authentication"))
        wants_testing = True

        nodes: List[NodeSpec] = []
        nodes.append(NodeSpec(id="research", depends_on=[], metadata={"task_hint": "research"}))
        nodes.append(NodeSpec(id="architect", depends_on=["research"], metadata={"task_hint": "architect"}))
        nodes.append(NodeSpec(id="database", depends_on=["architect"], metadata={"task_hint": "database"}))

        if wants_auth:
            nodes.append(NodeSpec(id="auth", depends_on=["database"], metadata={"task_hint": "auth"}))

        nodes.append(NodeSpec(id="crud", depends_on=["database"], metadata={"task_hint": "crud"}))

        if wants_frontend:
            nodes.append(NodeSpec(id="frontend", depends_on=["crud"], metadata={"task_hint": "frontend"}))

        if wants_docker:
            nodes.append(NodeSpec(id="docker", depends_on=["crud"], metadata={"task_hint": "docker"}))

        if wants_ci:
            nodes.append(NodeSpec(id="ci", depends_on=["crud"], metadata={"task_hint": "ci"}))

        nodes.append(NodeSpec(id="executor", depends_on=["crud"] + (["frontend"] if wants_frontend else []), metadata={"task_hint": "executor"}))

        if wants_testing:
            test_deps = ["executor"]
            if wants_docker:
                test_deps.append("docker")
            if wants_ci:
                test_deps.append("ci")
            if wants_frontend:
                test_deps.append("frontend")
            nodes.append(NodeSpec(id="testing", depends_on=test_deps, metadata={"task_hint": "testing"}))

        nodes.append(NodeSpec(id="reviewer", depends_on=["testing"], metadata={"task_hint": "review"}))

        nodes.append(NodeSpec(id="documentation", depends_on=["reviewer"], metadata={"task_hint": "docs", "when": "review_approved"}))

        if backend_only:
            nodes = [node for node in nodes if node.id not in {"frontend", "docker", "ci"}]

        return {"nodes": [n.__dict__ for n in nodes]}


# default planner instance
planner = Planner()
