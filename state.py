import operator
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
    extraction_retries: int
    audit_log: Annotated[list, operator.add]