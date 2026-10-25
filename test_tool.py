from agents.tools import verify_ltv

# Harbourside: £1.2M loan, £1.85M valuation, stated LTV 64.9%
print(verify_ltv.invoke({"loan_amount": 1200000, "collateral_valuation": 1850000, "stated_ltv_percent": 64.9}))

# A made-up mismatch: stated 70%, but the numbers give much more
print(verify_ltv.invoke({"loan_amount": 2400000, "collateral_valuation": 2925000, "stated_ltv_percent": 70.0}))