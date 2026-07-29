from __future__ import annotations

from dataclasses import dataclass
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from backend.app.core.config import settings
from backend.app.core.json_utils import parse_json_object
from backend.app.core.prompts import load_prompt
from backend.app.graph.state import AgentState


def _default_plan(user_request: str) -> dict[str, object]:
    lowered = user_request.lower()
    database = "SQLite"
    if any(keyword in lowered for keyword in ["store", "commerce", "payment", "analytics", "admin"]):
        database = "PostgreSQL"

    authentication = "JWT"
    orm = "SQLAlchemy"
    pattern = "Layered architecture with service and repository boundaries"
    folder_structure = "app/core, app/routes, app/models, app/services, tests, docs"

    notes = [
        "Use FastAPI with dependency injection for request-scoped services.",
        f"Use {database} for persistence and {orm} for data access.",
        "Keep auth isolated in a dedicated security module.",
    ]
    return {
        "backend": "FastAPI",
        "database": database,
        "authentication": authentication,
        "orm": orm,
        "pattern": pattern,
        "folder_structure": folder_structure,
        "notes": notes,
    }


@dataclass
class ArchitectAgent:
    def _client(self) -> ChatGroq:
        return ChatGroq(model=settings.groq_model, groq_api_key=settings.groq_api_key, temperature=0)

    def run(self, state: AgentState) -> dict[str, object]:
        user_request = state["user_request"]

        if settings.groq_api_key:
            prompt = load_prompt("architect")
            response = self._client().invoke([SystemMessage(content=prompt), HumanMessage(content=user_request)])
            payload = parse_json_object(str(response.content))
        else:
            payload = _default_plan(user_request)

        architecture = {
            "backend": str(payload.get("backend", "FastAPI")),
            "database": str(payload.get("database", "SQLite")),
            "authentication": str(payload.get("authentication", "JWT")),
            "orm": str(payload.get("orm", "SQLAlchemy")),
            "pattern": str(payload.get("pattern", "Layered architecture")),
            "folder_structure": str(payload.get("folder_structure", "app, tests, docs")),
            "notes": list(payload.get("notes", [])),
        }
        return {
            "architecture": architecture,
            "architect_summary": f"Selected {architecture['backend']} + {architecture['database']} for the backend.",
        }