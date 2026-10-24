from datetime import datetime
from langgraph.types import interrupt

from state import DealState, log_entry


def build_review_pack(state: DealState) -> dict:
    """Everything the credit officer needs to see, gathered from the folder."""
    terms = state.get("terms") or {}
    risk = state.get("risk")
    completeness = state.get("completeness") or {}

    if risk:
        ai_recommendation = risk["recommendation"]
    else:
        ai_recommendation = "Refer"   # incomplete applications are referred by default

    failed_rules = [
        f"{r['rule_id']} ({r['severity']}): {r['description']}. Actual: {r['actual_value']}"
        for r in (state.get("compliance_results") or [])
        if r["status"] != "PASS"
    ]

    return {
        "reference": terms.get("reference", "Not extracted"),
        "borrower": terms.get("borrower_name", "Not extracted"),
        "loan_amount": terms.get("loan_amount"),
        "missing_sections": completeness.get("missing_sections", []),
        "ai_recommendation": ai_recommendation,
        "risk_rating": risk["risk_rating"] if risk else "Not assessed",
        "failed_rules": failed_rules,
        "summary": risk["summary"] if risk else "Application incomplete; not assessed by the AI agents.",
    }


def human_review_node(state: DealState) -> dict:
    pack = build_review_pack(state)

    # The graph PAUSES here. Whatever the credit officer submits comes back as `response`.
    response = interrupt(pack)

    decision = {
        "ai_recommendation": pack["ai_recommendation"],
        "final_decision": response["final_decision"],
        "action": response["action"],            # "accepted" or "overridden"
        "reason": response.get("reason", ""),
        "officer": response["officer"],
        "decided_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    if decision["action"] == "accepted":
        message = f"{decision['officer']} accepted AI recommendation: {decision['final_decision']}"
    else:
        message = (f"{decision['officer']} overrode AI recommendation "
                   f"({decision['ai_recommendation']} → {decision['final_decision']}). "
                   f"Reason: {decision['reason']}")

    return {
        "human_decision": decision,
        "audit_log": [log_entry("Credit officer", message)],
    }