from __future__ import annotations

from dataclasses import dataclass
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.json_utils import parse_json_object
from app.core.prompts import load_prompt
from app.graph.state import AgentState


def _infer_project_name(user_request: str) -> str:
    lowered = user_request.lower()
    if "todo" in lowered:
        return "Todo API"
    if "expense" in lowered:
        return "Expense Tracker API"
    if "blog" in lowered:
        return "Blog Backend"

    match = re.search(r"build (?:a |an )?(.+?)(?: with| using| for|$)", lowered)
    if match:
        candidate = match.group(1).strip()
        if candidate:
            return candidate.title()

    return "FastAPI Project"


@dataclass
class SupervisorAgent:
    def _client(self) -> ChatGroq:
        return ChatGroq(model=settings.groq_model, groq_api_key=settings.groq_api_key, temperature=0)

    def _fallback(self, user_request: str) -> dict[str, object]:
        project_name = _infer_project_name(user_request)
        return {
            "project_name": project_name,
            "architecture": (
                "User request -> Supervisor -> Coder -> Reviewer -> Persisted project bundle"
            ),
            "tasks": [
                "Clarify the project scope and core backend requirements",
                "Generate the FastAPI backend template and supporting files",
                "Review the generated code for security and quality issues",
            ],
            "summary": (
                f"Planned {project_name} as a FastAPI backend with one coding pass and one reviewer pass."
            ),
        }

    def run(self, state: AgentState) -> dict[str, object]:
        user_request = state["user_request"]

        if settings.groq_api_key:
            prompt = load_prompt("supervisor")
            response = self._client().invoke(
                [
                    SystemMessage(content=prompt),
                    HumanMessage(content=user_request),
                ]
            )
            payload = parse_json_object(str(response.content))
        else:
            payload = self._fallback(user_request)

        project_name = str(payload.get("project_name", _infer_project_name(user_request)))
        return {
            "project_name": project_name,
            "architecture": str(payload.get("architecture", "")),
            "tasks": list(payload.get("tasks", [])),
            "supervisor_summary": str(payload.get("summary", "")),
        }
