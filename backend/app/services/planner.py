from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Any


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
        # naive rules: always include database, crud, tests; add auth if prompt mentions auth/jwt
        nodes: List[NodeSpec] = []
        nodes.append(NodeSpec(id="database", depends_on=[]))
        # add auth if requested
        if any(k in prompt.lower() for k in ("auth", "jwt", "login", "signup", "authentication")):
            nodes.append(NodeSpec(id="auth", depends_on=["database"]))
        nodes.append(NodeSpec(id="crud", depends_on=["database"]))
        depends = [n.id for n in nodes if n.id in ("auth", "crud")]
        nodes.append(NodeSpec(id="tests", depends_on=depends))

        # always include research & documentation
        nodes.insert(0, NodeSpec(id="research", depends_on=[]))
        nodes.append(NodeSpec(id="documentation", depends_on=["tests"]))

        return {"nodes": [n.__dict__ for n in nodes]}


# default planner instance
planner = Planner()
