import json
from agents.extractor import extractor_node
from agents.compliance import compliance_node
from agents.risk import risk_node

with open("data/lending_policy.json", encoding="utf-8") as f:
    policy = json.load(f)

for filename in ["deal_a_clean.txt", "deal_b_breach.txt"]:
    with open(f"data/{filename}", encoding="utf-8") as f:
        document = f.read()

    state = {"document": document, "policy": policy}
    state.update(extractor_node(state))     # Agent 2 adds the terms to the folder
    state.update(compliance_node(state))    # Agent 3 adds the rule results
    output = risk_node(state)               # Agent 4 reads both

    risk = output["risk"]
    print(f"\n=== {filename} ===")
    print(f"Risk rating:    {risk['risk_rating']}")
    print(f"Recommendation: {risk['recommendation']}")
    print("Key risks:")
    for item in risk["key_risks"]:
        print(f"  - {item}")
    print("Mitigants:")
    for item in risk["mitigants"]:
        print(f"  - {item}")
    print(f"Summary: {risk['summary']}")
    print(output["audit_log"])