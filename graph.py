from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from state import DealState
from agents.orchestrator import orchestrator_node
from agents.completeness import completeness_node
from agents.extractor import extractor_node
from agents.compliance import compliance_node
from agents.risk import risk_node
from agents.human_review import human_review_node

AGENTS = {
    "completeness": completeness_node,
    "extractor": extractor_node,
    "compliance": compliance_node,
    "risk": risk_node,
    "human_review": human_review_node,
}


def build_graph():
    builder = StateGraph(DealState)

    # The hub
    builder.add_node("orchestrator", orchestrator_node)

    # The spokes: every agent (and the credit officer) reports back to the orchestrator
    for name, node in AGENTS.items():
        builder.add_node(name, node)
        builder.add_edge(name, "orchestrator")

    builder.add_edge(START, "orchestrator")

    builder.add_conditional_edges(
        "orchestrator",
        lambda state: state["next_step"],
        {
            "completeness": "completeness",
            "extractor": "extractor",
            "compliance": "compliance",
            "risk": "risk",
            "human_review": "human_review",   # now a real step
            "end": END,
        },
    )

    # The checkpointer saves the folder while the graph is paused for the credit officer
    return builder.compile(checkpointer=MemorySaver())