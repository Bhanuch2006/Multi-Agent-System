from __future__ import annotations

from dataclasses import dataclass
import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.json_utils import parse_json_object
from app.core.prompts import load_prompt
from app.graph.state import AgentState


def _fallback_review(project_files: dict[str, str]) -> dict[str, object]:
    security_file = project_files.get("app/core/security.py", "")
    findings: list[str] = []
    suggestions: list[str] = []

    if 'SECRET_KEY = "dev-secret"' in security_file:
        findings.append("JWT secret is hardcoded in app/core/security.py.")
        suggestions.append("Read JWT_SECRET from the environment and fail fast when it is missing.")

    if "TODO" in security_file or "todo" in security_file.lower():
        findings.append("The generated code contains a placeholder that should be removed.")

    if findings:
        return {
            "verdict": "needs_revision",
            "needs_revision": True,
            "findings": findings,
            "suggestions": suggestions,
        }

    return {
        "verdict": "approved",
        "needs_revision": False,
        "findings": [],
        "suggestions": ["No blocking issues found."],
    }


@dataclass
class ReviewerAgent:
    def _client(self) -> ChatGroq:
        return ChatGroq(model=settings.groq_model, groq_api_key=settings.groq_api_key, temperature=0)

    def run(self, state: AgentState) -> dict[str, object]:
        project_files = dict(state.get("project_files", {}))

        if settings.groq_api_key:
            prompt = load_prompt("reviewer")
            payload_text = json.dumps(
                {
                    "project_name": state.get("project_name"),
                    "user_request": state.get("user_request"),
                    "tasks": state.get("tasks", []),
                    "project_files": project_files,
                    "revision_count": state.get("revision_count", 0),
                },
                indent=2,
            )
            response = self._client().invoke(
                [
                    SystemMessage(content=prompt),
                    HumanMessage(content=payload_text),
                ]
            )
            payload = parse_json_object(str(response.content))
        else:
            payload = _fallback_review(project_files)

        return {
            "review": {
                "verdict": str(payload.get("verdict", "needs_revision")),
                "needs_revision": bool(payload.get("needs_revision", False)),
                "findings": list(payload.get("findings", [])),
                "suggestions": list(payload.get("suggestions", [])),
            }
        }
