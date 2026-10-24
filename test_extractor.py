import json
from agents.extractor import extractor_node

for filename in ["deal_a_clean.txt", "deal_b_breach.txt"]:
    with open(f"data/{filename}", encoding="utf-8") as f:
        document = f.read()

    output = extractor_node({"document": document})

    print(f"\n=== {filename} ===")
    print(json.dumps(output["terms"], indent=2))
    print(output["audit_log"])
