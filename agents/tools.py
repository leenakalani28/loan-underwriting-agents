from langchain_core.tools import tool


@tool
def verify_ltv(loan_amount: float, collateral_valuation: float, stated_ltv_percent: float) -> dict:
    """Recalculates the loan-to-value ratio from the loan amount and the collateral valuation,
    and checks it against the LTV stated in the application. Use this before relying on any LTV figure."""
    if collateral_valuation <= 0:
        return {"error": "Collateral valuation must be greater than zero"}

    calculated = round(loan_amount / collateral_valuation * 100, 1)
    difference = round(calculated - stated_ltv_percent, 1)

    return {
        "calculated_ltv_percent": calculated,
        "stated_ltv_percent": stated_ltv_percent,
        "difference_points": difference,
        "consistent": abs(difference) <= 0.5,   # allow for rounding in the application
    }