from __future__ import annotations

from dataclasses import dataclass
import json
from datetime import datetime
from time import perf_counter

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from backend.app.core.config import settings
from backend.app.core.json_utils import parse_json_object
from backend.app.core.prompts import load_prompt
from backend.app.graph.state import AgentState
from backend.app.models.agents import ReviewOutput, AgentMessage, AgentMetrics


def _fallback_review(state: AgentState) -> dict[str, object]:
    project_files = dict(state.get("project_files", {}))
    security_file = project_files.get("app/core/security.py", "")
    findings: list[str] = []
    suggestions: list[str] = []

    if 'SECRET_KEY = os.getenv("JWT_SECRET")' not in security_file:
        findings.append("JWT secret is not loaded from the environment.")
        suggestions.append("Read JWT_SECRET from the environment and fail fast when it is missing.")

    if "passlib" not in project_files.get("requirements.txt", ""):
        findings.append("Password hashing dependency is missing.")
        suggestions.append("Add passlib[bcrypt] to requirements.")

    if "README.md" not in project_files:
        findings.append("Documentation was not generated yet.")
        suggestions.append("Add a README in the documentation step.")

    score = 100 - len(findings) * 10
    approved = score >= 90
    return {
        "score": score,
        "approved": approved,
        "findings": findings,
        "suggestions": suggestions or (["No blocking issues found."] if approved else suggestions),
    }


@dataclass
class ReviewerAgent:
    def _client(self) -> ChatGroq:
        return ChatGroq(model=settings.groq_model, groq_api_key=settings.groq_api_key, temperature=0)

    def run(self, state: AgentState) -> dict[str, object]:
        project_files = dict(state.get("project_files", {}))
        start = perf_counter()
        start_time = datetime.utcnow()
        if settings.groq_api_key:
            prompt = load_prompt("reviewer")
            payload_text = json.dumps(
                {
                    "project_name": state.get("project_name"),
                    "user_request": state.get("user_request"),
                    "task_list": state.get("task_list", []),
                    "architecture": state.get("architecture", {}),
                    "research_notes": state.get("research_notes", []),
                    "project_files": project_files,
                    "revision_count": state.get("revision_count", 0),
                },
                indent=2,
            )
            response = self._client().invoke([SystemMessage(content=prompt), HumanMessage(content=payload_text)])
            payload = parse_json_object(str(response.content))
        else:
            payload = _fallback_review(state)

        end = perf_counter()
        end_time = datetime.utcnow()

        review = ReviewOutput.model_validate(payload)

        messages = []
        if not review.approved:
            # send a high-priority message to FixAgent/Coder
            messages.append(
                AgentMessage(
                    from_agent="Reviewer",
                    to_agent="FixAgent",
                    priority="high",
                    message="Issues found: " + "; ".join(review.findings),
                    timestamp=start_time,
                ).model_dump()
            )

        metrics = AgentMetrics(
            agent="Reviewer",
            start_time=start_time,
            end_time=end_time,
            tokens=0,
            cost=0.0,
            latency=end - start,
        ).model_dump()

        return {
            "review": review.model_dump(),
            "messages": messages,
            "metrics": metrics,
        }
