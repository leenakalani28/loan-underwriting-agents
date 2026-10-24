import sys
import json
from langgraph.types import Command
from graph import build_graph

filename = sys.argv[1] if len(sys.argv) > 1 else "deal_a_clean.txt"

with open("data/lending_policy.json", encoding="utf-8") as f:
    policy = json.load(f)
with open(f"data/{filename}", encoding="utf-8") as f:
    document = f.read()

initial_state = {
    "document": document,
    "policy": policy,
    "completeness": None,
    "terms": None,
    "compliance_results": None,
    "risk": None,
    "human_decision": None,
    "next_step": None,
    "extraction_retries": 0,
    "audit_log": [],
}

graph = build_graph()

# Each deal gets its own "thread": the ID the checkpointer saves the folder under
config = {"configurable": {"thread_id": filename}}


def show_review_pack(pack: dict):
    print("\n" + "=" * 70)
    print("CREDIT OFFICER REVIEW")
    print("=" * 70)
    print(f"Reference:         {pack['reference']}")
    print(f"Borrower:          {pack['borrower']}")
    if pack["loan_amount"]:
        print(f"Loan amount:       £{pack['loan_amount']:,.0f}")
    if pack["missing_sections"]:
        print(f"Missing sections:  {', '.join(pack['missing_sections'])}")
    print(f"AI risk rating:    {pack['risk_rating']}")
    print(f"AI recommendation: {pack['ai_recommendation']}")
    if pack["failed_rules"]:
        print("Policy exceptions:")
        for rule in pack["failed_rules"]:
            print(f"  - {rule}")
    print(f"\nSummary: {pack['summary']}")
    print("=" * 70)


def ask(question: str, allowed: list[str]) -> str:
    """Keeps asking until the officer types one of the allowed answers."""
    while True:
        answer = input(question).strip().lower()
        if answer in allowed:
            return answer
        print(f"Please type one of: {', '.join(allowed)}")


def get_officer_decision(pack: dict) -> dict:
    officer = input("\nYour name: ").strip() or "Credit officer"
    choice = ask(f"Accept AI recommendation ({pack['ai_recommendation']})? [a]ccept / [o]verride: ", ["a", "o"])

    if choice == "a":
        return {"action": "accepted", "final_decision": pack["ai_recommendation"], "officer": officer}

    outcomes = {"approve": "Approve", "refer": "Refer", "decline": "Decline"}
    final = ask("Your decision [approve / refer / decline]: ", list(outcomes))
    reason = ""
    while not reason:
        reason = input("Reason for override (required): ").strip()
    return {"action": "overridden", "final_decision": outcomes[final], "reason": reason, "officer": officer}


# ---- Run 1: the agents work until the graph pauses for the credit officer ----
graph.invoke(initial_state, config)

# ---- Is the graph paused, waiting for a human? ----
snapshot = graph.get_state(config)
if snapshot.next:
    pack = snapshot.tasks[0].interrupts[0].value
    show_review_pack(pack)
    decision = get_officer_decision(pack)

    # ---- Run 2: resume the graph with the officer's decision ----
    graph.invoke(Command(resume=decision), config)

final_state = graph.get_state(config).values

print(f"\n=== AUDIT LOG: {filename} ===")
for entry in final_state["audit_log"]:
    print(f"{entry['time']}  {entry['agent']:<22} {entry['message']}")

hd = final_state["human_decision"]
print(f"\nFINAL DECISION: {hd['final_decision']} "
      f"(AI recommended {hd['ai_recommendation']}; {hd['action']} by {hd['officer']})")