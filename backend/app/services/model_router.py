from __future__ import annotations

from dataclasses import dataclass

from backend.app.core.config import settings


@dataclass(frozen=True)
class ModelRoute:
    agent: str
    model: str
    reason: str


class ModelRouter:
    def resolve(self, agent: str, task_hint: str | None = None) -> ModelRoute:
        if agent in {"research", "researcher"}:
            return ModelRoute(agent=agent, model=settings.research_model, reason="research optimization")
        if agent in {"reviewer", "review"}:
            return ModelRoute(agent=agent, model=settings.review_model, reason="analysis/reasoning")
        if agent in {"documentation", "docs"}:
            return ModelRoute(agent=agent, model=settings.docs_model, reason="summarization/documentation")
        return ModelRoute(agent=agent, model=settings.code_model, reason="code generation/default")


model_router = ModelRouter()
