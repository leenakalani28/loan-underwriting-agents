import operator
from datetime import datetime
from typing import TypedDict, Optional, Annotated


class DealState(TypedDict):
    # Input
    document: str
    policy: dict

    # Agent outputs (stored as plain dicts so the checkpointer can save them)
    completeness: Optional[dict]
    terms: Optional[dict]
    compliance_results: Optional[list]
    risk: Optional[dict]

    # Human review
    human_decision: Optional[dict]

    # Orchestration
    next_step: Optional[str]
    extraction_retries: int
    audit_log: Annotated[list, operator.add]


def log_entry(agent: str, message: str) -> dict:
    """One line for the audit log: when, which agent, what it did."""
    return {
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": agent,
        "message": message,
    }