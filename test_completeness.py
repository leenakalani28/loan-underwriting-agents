import json
from agents.completeness import completeness_node

with open("data/lending_policy.json", encoding="utf-8") as f:
    policy = json.load(f)

for filename in ["deal_a_clean.txt", "deal_c_incomplete.txt"]:
    with open(f"data/{filename}", encoding="utf-8") as f:
        document = f.read()

    state = {"document": document, "policy": policy}
    output = completeness_node(state)

    print(f"\n=== {filename} ===")
    print(output["completeness"])
    print(output["audit_log"])