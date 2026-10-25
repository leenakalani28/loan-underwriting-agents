"""Turns each agent's update from the graph into what the step cards show."""

STEP_LABELS = {
    "completeness": "Completeness check",
    "extractor": "Term extraction",
    "compliance": "Policy check",
    "risk": "Risk assessment",
    "human_review": "Credit officer",
}


def new_steps() -> dict:
    """All five steps start as 'pending'."""
    return {key: {"label": label, "status": "pending", "detail": "Waiting"}
            for key, label in STEP_LABELS.items()}


def apply_update(steps: dict, node: str, data: dict):
    """Updates the step cards based on which node just finished and what it returned."""

    # The orchestrator tells us which step is starting next
    if node == "orchestrator":
        next_step = data.get("next_step")
        if next_step == "human_review":
            # Any agents that never ran were skipped (the incomplete-application short-circuit)
            for key in ["extractor", "compliance", "risk"]:
                if steps[key]["status"] == "pending":
                    steps[key].update(status="skipped", detail="Skipped: application incomplete")
            steps["human_review"].update(status="awaiting", detail="Awaiting decision")
        elif next_step in steps:
            retry = next_step == "extractor" and steps["extractor"]["status"] != "pending"
            steps[next_step].update(status="running",
                                    detail="Re-checking missed terms" if retry else "Working…")

    elif node == "completeness":
        result = data["completeness"]
        if result["is_complete"]:
            steps["completeness"].update(status="done", detail="All sections present")
        else:
            missing = len(result["missing_sections"])
            steps["completeness"].update(status="warn", detail=f"{missing} sections missing")

    elif node == "extractor":
        terms = data["terms"]
        filled = sum(1 for value in terms.values() if value not in (None, []))
        steps["extractor"].update(status="done", detail=f"{filled} of {len(terms)} terms extracted")

    elif node == "compliance":
        results = data["compliance_results"]
        failed = sum(1 for r in results if r["status"] == "FAIL")
        unverified = sum(1 for r in results if r["status"] == "UNABLE_TO_VERIFY")
        if failed:
            steps["compliance"].update(status="fail", detail=f"{failed} of {len(results)} rules failed")
        elif unverified:
            steps["compliance"].update(status="warn", detail=f"{unverified} rules unverified")
        else:
            steps["compliance"].update(status="done", detail=f"All {len(results)} rules passed")

    elif node == "risk":
        risk = data["risk"]
        status = {"Approve": "done", "Refer": "warn", "Decline": "fail"}[risk["recommendation"]]
        steps["risk"].update(status=status,
                             detail=f"{risk['risk_rating']} risk · {risk['recommendation']}")