from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents.coder import CoderAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.supervisor import SupervisorAgent
from app.core.config import settings
from app.graph.state import AgentState


def build_workflow():
    workflow = StateGraph(AgentState)

    supervisor = SupervisorAgent()
    coder = CoderAgent()
    reviewer = ReviewerAgent()

    def review_router(state: AgentState) -> str:
        review = dict(state.get("review", {}))
        revision_count = int(state.get("revision_count", 0))
        needs_revision = bool(review.get("needs_revision", False))

        if needs_revision and revision_count < settings.max_revision_cycles:
            return "coder"
        return END

    def run_supervisor(state: AgentState):
        updates = supervisor.run(state)
        return {**updates, "revision_count": int(state.get("revision_count", 0))}

    def run_coder(state: AgentState):
        current_revision = int(state.get("revision_count", 0))
        updates = coder.run(state)
        return {**updates, "revision_count": current_revision + 1}

    def run_reviewer(state: AgentState):
        return reviewer.run(state)

    workflow.add_node("supervisor", run_supervisor)
    workflow.add_node("coder", run_coder)
    workflow.add_node("reviewer", run_reviewer)

    workflow.add_edge(START, "supervisor")
    workflow.add_edge("supervisor", "coder")
    workflow.add_edge("coder", "reviewer")
    workflow.add_conditional_edges("reviewer", review_router, {"coder": "coder", END: END})

    return workflow.compile()
