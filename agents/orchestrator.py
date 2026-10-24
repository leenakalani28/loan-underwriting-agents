from agents.extractor import missing_mandatory
from state import DealState, log_entry

MAX_EXTRACTION_RETRIES = 1


def decide_next_step(state: DealState) -> tuple[str, str]:
    """Looks at the folder and returns (next step, reason for the audit log)."""

    # Checked FIRST: once the credit officer has decided, the deal is finished
    if state.get("human_decision") is not None:
        return "end", "Credit officer decision recorded; pipeline complete"

    if state.get("completeness") is None:
        return "completeness", "New application received; checking completeness"

    if not state["completeness"]["is_complete"]:
        missing = ", ".join(state["completeness"]["missing_sections"])
        return "human_review", f"Incomplete application (missing {missing}); short-circuiting to credit officer"

    if state.get("terms") is None:
        return "extractor", "Application complete; extracting loan terms"

    missing = missing_mandatory(state["terms"])
    if missing and state.get("extraction_retries", 0) < MAX_EXTRACTION_RETRIES:
        return "extractor", f"Mandatory terms missing ({', '.join(missing)}); sending back to extractor"

    if state.get("compliance_results") is None:
        return "compliance", "Terms extracted; checking against lending policy"

    if state.get("risk") is None:
        return "risk", "Compliance checked; requesting risk assessment"

    return "human_review", "Review complete; passing to credit officer for decision"


def orchestrator_node(state: DealState) -> dict:
    next_step, reason = decide_next_step(state)
    return {
        "next_step": next_step,
        "audit_log": [log_entry("Orchestrator", f"{reason} → {next_step}")],
    }