import json
from agents.extractor import extractor_node
from agents.compliance import compliance_node

with open("data/lending_policy.json", encoding="utf-8") as f:
    policy = json.load(f)

for filename in ["deal_a_clean.txt", "deal_b_breach.txt"]:
    with open(f"data/{filename}", encoding="utf-8") as f:
        document = f.read()

    # Agent 2 fills in the terms...
    extracted = extractor_node({"document": document})
    # ...and Agent 3 reads them from the "folder"
    state = {"terms": extracted["terms"], "policy": policy}
    output = compliance_node(state)

    print(f"\n=== {filename} ===")
    for r in output["compliance_results"]:
        print(f"{r['rule_id']}  {r['status']:<17} {r['actual_value']}")
    print(output["audit_log"])