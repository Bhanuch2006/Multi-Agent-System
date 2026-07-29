from __future__ import annotations

from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from backend.app.core.config import settings
from backend.app.core.json_utils import parse_json_object
from backend.app.core.prompts import load_prompt
from backend.app.graph.state import AgentState
from backend.app.tools.search import SearchTool


def _fallback_notes(architecture: dict[str, object]) -> dict[str, object]:
    backend = str(architecture.get("backend", "FastAPI"))
    database = str(architecture.get("database", "SQLite"))
    orm = str(architecture.get("orm", "SQLAlchemy"))
    notes = [
        f"Use {backend} dependency injection for request-scoped services.",
        f"Prefer {orm} 2.x style ORM patterns for persistence.",
        f"Keep {database} access behind a small repository or service layer.",
        "Use bcrypt for password hashing and short-lived JWT access tokens.",
    ]
    sources = [
        "FastAPI docs",
        "SQLAlchemy docs",
        "Python-JOSE docs",
        "Passlib docs",
    ]
    return {"notes": notes, "sources": sources}


@dataclass
class ResearchAgent:
    search_tool: SearchTool = SearchTool()

    def _client(self) -> ChatGroq:
        return ChatGroq(model=settings.groq_model, groq_api_key=settings.groq_api_key, temperature=0)

    def run(self, state: AgentState) -> dict[str, object]:
        architecture = dict(state.get("architecture", {}))
        user_request = state["user_request"]

        if settings.groq_api_key:
            prompt = load_prompt("researcher")
            payload_text = {
                "user_request": user_request,
                "architecture": architecture,
            }
            response = self._client().invoke(
                [SystemMessage(content=prompt), HumanMessage(content=str(payload_text))]
            )
            payload = parse_json_object(str(response.content))
        else:
            payload = _fallback_notes(architecture)

        notes = list(payload.get("notes", []))
        sources = list(payload.get("sources", []))

        if not notes:
            search_terms = [
                f"FastAPI {user_request} best practices",
                f"SQLAlchemy 2.x official docs",
                f"JWT authentication FastAPI official docs",
            ]
            for query in search_terms:
                results = self.search_tool.search(query, max_results=2)
                for result in results:
                    sources.append(result.url)
                    if result.snippet:
                        notes.append(result.snippet)
                    elif result.title:
                        notes.append(result.title)

        if not notes:
            fallback = _fallback_notes(architecture)
            notes = list(fallback["notes"])
            sources = list(fallback["sources"])

        return {
            "research_notes": notes,
            "research_sources": sources,
            "research_summary": f"Collected {len(notes)} implementation notes.",
        }