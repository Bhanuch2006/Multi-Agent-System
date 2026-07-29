from __future__ import annotations

from dataclasses import dataclass
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from backend.app.core.config import settings
from backend.app.core.json_utils import parse_json_object
from backend.app.core.prompts import load_prompt
from backend.app.graph.state import AgentState


def _infer_project_name(user_request: str) -> str:
    lowered = user_request.lower()
    if "todo" in lowered:
        return "Todo API"
    if "e-commerce" in lowered or "ecommerce" in lowered:
        return "Ecommerce API"
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
        task_list = [
            "Define the architecture",
            "Research implementation best practices",
            "Generate the backend code",
            "Review the implementation",
            "Write project documentation",
        ]
        return {
            "project_name": project_name,
            "task_list": task_list,
            "summary": f"Planned {project_name} as a staged engineering workflow.",
            "include_research": True,
            "include_documentation": True,
        }

    def run(self, state: AgentState) -> dict[str, object]:
        user_request = state["user_request"]

        if settings.groq_api_key:
            prompt = load_prompt("supervisor")
            response = self._client().invoke(
                [SystemMessage(content=prompt), HumanMessage(content=user_request)]
            )
            payload = parse_json_object(str(response.content))
        else:
            payload = self._fallback(user_request)

        project_name = str(payload.get("project_name", _infer_project_name(user_request)))
        return {
            "project_name": project_name,
            "task_list": list(payload.get("task_list", [])),
            "supervisor_summary": str(payload.get("summary", "")),
        }
