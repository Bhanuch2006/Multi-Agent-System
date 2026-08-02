from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from backend.app.agents.architect import ArchitectAgent
from backend.app.agents.coder import CoderAgent
from backend.app.agents.documentation import DocumentationAgent
from backend.app.agents.researcher import ResearchAgent
from backend.app.agents.reviewer import ReviewerAgent
from backend.app.agents.supervisor import SupervisorAgent
from backend.app.agents.fix_agent import FixAgent
from backend.app.core.config import settings
from backend.app.graph.state import AgentState


def build_workflow():
    workflow = StateGraph(AgentState)

    supervisor = SupervisorAgent()
    architect = ArchitectAgent()
    researcher = ResearchAgent()
    coder = CoderAgent()
    reviewer = ReviewerAgent()
    documentation = DocumentationAgent()

    def run_supervisor(state: AgentState):
        updates = supervisor.run(state)
        return {**updates, "current_agent": "Supervisor", "progress": 10, "status": "running"}

    def run_architect(state: AgentState):
        updates = architect.run(state)
        return {**updates, "current_agent": "Architect", "progress": 25}

    def run_researcher(state: AgentState):
        updates = researcher.run(state)
        return {**updates, "current_agent": "Research", "progress": 40}

    def run_coder(state: AgentState):
        updates = coder.run(state)
        current_revision = int(state.get("revision_count", 0))
        return {**updates, "current_agent": "Coding", "progress": 65, "revision_count": current_revision + 1}

    def run_reviewer(state: AgentState):
        updates = reviewer.run(state)
        return {**updates, "current_agent": "Review", "progress": 80}

    def run_documentation(state: AgentState):
        updates = documentation.run(state)
        return {**updates, "current_agent": "Documentation", "progress": 100, "status": "completed"}

    def review_router(state: AgentState) -> str:
        review = dict(state.get("review", {}))
        # support structured review with score
        score = int(review.get("score", 0)) if review else 0
        revision_count = int(state.get("revision_count", 0))

        # threshold: >=90 proceed to documentation, else go to FixAgent
        if score >= 90:
            return "documentation_step"

        if revision_count < settings.max_revision_cycles:
            return "fix_agent"
        return "documentation_step"

    workflow.add_node("supervisor", run_supervisor)
    workflow.add_node("architect", run_architect)
    workflow.add_node("researcher", run_researcher)
    workflow.add_node("coder", run_coder)
    workflow.add_node("reviewer", run_reviewer)
    workflow.add_node("fix_agent", lambda s: FixAgent().run(s))
    workflow.add_node("documentation_step", run_documentation)

    workflow.add_edge(START, "supervisor")
    workflow.add_edge("supervisor", "architect")
    workflow.add_edge("architect", "researcher")
    # run architect, researcher, and an optional database design step in parallel
    workflow.add_edge("researcher", "coder")
    workflow.add_edge("architect", "coder")
    workflow.add_edge("coder", "reviewer")
    workflow.add_conditional_edges("reviewer", review_router, {"coder": "coder", "fix_agent": "fix_agent", "documentation_step": "documentation_step"})
    workflow.add_edge("fix_agent", "reviewer")
    workflow.add_edge("documentation_step", END)
    return workflow.compile()
