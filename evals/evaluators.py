"""Evaluators for the SME loan underwriting pipeline.

Each function receives the pipeline's outputs for one case and the answer key
(reference_outputs), and returns a score. LangSmith calls them for every case.

Code-based (deterministic): decision accuracy, breach detection, trajectory,
extraction accuracy, latency, errors.
LLM-as-judge: narrative faithfulness of the risk agent's written assessment.
"""
import json
import os
import time
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

HIGH_SEVERITY = {"R1", "R2", "R5", "R8", "R9", "R10"}


# ---------------------------------------------------------------- 1. Decision accuracy
def decision_accuracy(outputs: dict, reference_outputs: dict) -> dict:
    """Did the AI recommend a correct outcome? (Stricter outcomes are accepted where the answer key allows.)"""
    got = outputs.get("recommendation")
    ok = got in reference_outputs["acceptable_recommendations"]
    return {"key": "decision_accuracy", "score": int(ok),
            "comment": f"Recommended {got}; expected {reference_outputs['expected_recommendation']}"
                       f" (acceptable: {', '.join(reference_outputs['acceptable_recommendations'])})"}


# ---------------------------------------------------------------- 2. Breach detection
def breach_detection(outputs: dict, reference_outputs: dict) -> dict:
    """Recall of expected policy breaches, recall of high-severity breaches, and false alarms.
    Only applies to cases that should go through the full review."""
    if reference_outputs["expected_route"] != "full":
        return {"results": []}
    expected = set(reference_outputs["expected_non_pass_rules"])
    found = set(outputs.get("non_pass_rules") or [])
    results = []
    if expected:
        caught = expected & found
        results.append({"key": "breach_recall", "score": round(len(caught) / len(expected), 3),
                        "comment": f"Expected {sorted(expected)}; flagged {sorted(found)}; missed {sorted(expected - found)}"})
    expected_high = expected & HIGH_SEVERITY
    if expected_high:
        results.append({"key": "high_severity_recall", "score": round(len(expected_high & found) / len(expected_high), 3),
                        "comment": f"High-severity expected {sorted(expected_high)}; missed {sorted(expected_high - found)}"})
    false_alarms = found - expected
    results.append({"key": "no_false_alarms", "score": int(not false_alarms),
                    "comment": f"Rules flagged that should have passed: {sorted(false_alarms) or 'none'}"})
    return {"results": results}


# ---------------------------------------------------------------- 3. Trajectory
def trajectory(outputs: dict, reference_outputs: dict) -> dict:
    """Did the pipeline take the right path (full review vs short-circuit) and call the registry tool when it should?"""
    route_ok = outputs.get("route") == reference_outputs["expected_route"]
    tool_ok = bool(outputs.get("tool_called")) == bool(reference_outputs["expected_tool_call"])
    return {"key": "trajectory_correct", "score": int(route_ok and tool_ok),
            "comment": f"Route {outputs.get('route')} (expected {reference_outputs['expected_route']}); "
                       f"tool called {outputs.get('tool_called')} (expected {reference_outputs['expected_tool_call']})"}


# ---------------------------------------------------------------- 4. Extraction accuracy (diagnostic)
TOLERANCE = {"loan_amount": ("rel", 0.005), "ltv_percent": ("abs", 0.15), "dscr": ("abs", 0.011),
             "tenor_years": ("abs", 0.01), "years_trading": ("abs", 0.01), "net_debt_to_ebitda": ("abs", 0.011)}


def _field_ok(name, expected, got):
    if name == "personal_guarantee":
        if expected is None:  # "to be agreed": not in place, so false or empty are both right
            return got in (None, False)
        return got is expected
    if name == "company_number":
        return got is not None and str(got).strip().lstrip("0") == str(expected).strip().lstrip("0")
    if got is None:
        return False
    kind, tol = TOLERANCE[name]
    try:
        got = float(got)
    except (TypeError, ValueError):
        return False
    return abs(got - expected) <= (tol * abs(expected) if kind == "rel" else tol)


def extraction_accuracy(outputs: dict, reference_outputs: dict) -> dict:
    """Share of key loan terms the extractor got right (numbers within a small tolerance)."""
    expected = reference_outputs.get("expected_terms")
    terms = outputs.get("terms")
    if not expected or not terms:
        return {"results": []}
    wrong = [f"{k}: got {terms.get(k)!r}, expected {v!r}" for k, v in expected.items() if not _field_ok(k, v, terms.get(k))]
    return {"key": "extraction_accuracy", "score": round(1 - len(wrong) / len(expected), 3),
            "comment": "; ".join(wrong) or "All key terms correct"}


# ---------------------------------------------------------------- 5. Narrative faithfulness (LLM-as-judge)
class JudgeVerdict(BaseModel):
    failed_criteria: list[str] = Field(description="IDs of criteria that fail, e.g. ['C3']; empty if all pass")
    verdict: Literal["PASS", "FAIL"] = Field(description="FAIL if any criterion fails")
    reason: str = Field(description="One or two sentences explaining the verdict, quoting the problem text")


JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a senior credit risk reviewer at a UK bank auditing a risk assessment written by an AI agent "
     "for an SME secured loan. Judge it ONLY against the facts provided. Be strict but fair.\n\n"
     "Criteria (any failure means the verdict is FAIL):\n"
     "C1 Coverage: every rule with status FAIL or UNABLE_TO_VERIFY appears as a key risk.\n"
     "C2 Grounded: every fact stated (figures, names, guarantee terms, security, trading history) is supported "
     "by the extracted terms or the rule results. Nothing invented. A claim contradicted by a rule result "
     "(for example citing a trading history that the registry check found to be false) fails this criterion.\n"
     "C3 Genuine mitigants: no mitigant is a pass/fail entry requirement with no margin to measure.\n"
     "  NOT genuine (fail C3 if listed as a mitigant): KYC complete, audited accounts provided, sector not "
     "excluded, tenor within the limit, borrower found on the registry, covenants agreed, covenants set exactly "
     "at policy, trading history under 5 years, or any metric that only just meets its limit.\n"
     "  GENUINE (do NOT fail C3 for these): a metric with clear headroom against its limit, stated with the "
     "figure, e.g. LTV at least 5 points below 75%, DSCR at least 0.15x above 1.25x, net debt/EBITDA at least "
     "0.5x below 3.5x; an established trading history of 5 years or more (only if not contradicted by the "
     "registry check); collateral value well above the loan; a personal guarantee or extra security; covenants "
     "tighter than policy.\n"
     "  A single mitigant that bundles a genuine item with a non-genuine one (e.g. '12 years trading and KYC "
     "complete') fails C3, because the non-genuine part is still presented as a mitigant.\n"
     "  Judge each mitigant on its own: one non-genuine item fails C3; genuine items never do.\n"
     "C4 Accurate security: guarantees and security are described as stated, including any limits or amounts.\n"
     "C5 Case-specific check: {narrative_check}\n\n"
     "If C5 says 'none', treat it as passed."),
    ("human",
     "Extracted loan terms:\n{terms}\n\n"
     "Rule results:\n{rules}\n\n"
     "AI risk assessment to judge:\n"
     "Risk rating: {rating}\nRecommendation: {recommendation}\n"
     "Key risks:\n{risks}\nMitigants:\n{mitigants}\nSummary: {summary}"),
])

_judge = None


def _get_judge():
    """The judge model comes from JUDGE_MODEL in .env (falls back to the agent's model).
    Claude models (names starting 'claude') run on the Anthropic API; anything else runs on Groq."""
    global _judge
    if _judge is None:
        model = os.getenv("JUDGE_MODEL") or os.getenv("GROQ_MODEL")
        if model.startswith("claude"):
            from langchain_anthropic import ChatAnthropic
            llm = ChatAnthropic(model=model, max_tokens=800, max_retries=3)  # newer Claude models fix temperature
        else:
            llm = ChatGroq(model=model, temperature=0, max_tokens=800, max_retries=3)
        _judge = JUDGE_PROMPT | llm.with_structured_output(JudgeVerdict)
    return _judge


def _judge_with_retry(inputs: dict, attempts: int = 3):
    """Calls the judge, trying again if the model returns a badly formatted answer."""
    last_error = None
    for attempt in range(attempts):
        try:
            return _get_judge().invoke(inputs)
        except Exception as err:  # malformed structured answer or a temporary API error
            last_error = err
            time.sleep(5 * (attempt + 1))
    raise last_error


def narrative_faithfulness(outputs: dict, reference_outputs: dict) -> dict:
    """LLM-as-judge: is the risk agent's written assessment trustworthy?"""
    if not outputs.get("summary"):
        return {"results": []}  # short-circuited cases have no AI assessment to judge
    rules = "\n".join(f"{r['rule_id']} [{r['status']}] {r['description']}: {r['actual_value']}"
                      for r in outputs.get("rule_results") or [])
    bullet = lambda items: "\n".join(f"- {i}" for i in items) or "- (none)"
    try:
        v = _judge_with_retry({
            "narrative_check": reference_outputs.get("narrative_check") or "none",
            "terms": json.dumps(outputs.get("terms"), indent=2),
            "rules": rules,
            "rating": outputs.get("risk_rating"),
            "recommendation": outputs.get("recommendation"),
            "risks": bullet(outputs.get("key_risks") or []),
            "mitigants": bullet(outputs.get("mitigants") or []),
            "summary": outputs.get("summary"),
        })
    except Exception as err:
        return {"key": "narrative_faithfulness", "score": None, "comment": f"Judge error: {err}"}
    return {"key": "narrative_faithfulness", "score": int(v.verdict == "PASS"),
            "comment": f"{v.verdict} {v.failed_criteria}: {v.reason}"}


# ---------------------------------------------------------------- 6. Latency and errors
def latency(outputs: dict) -> dict:
    return {"key": "latency_s", "score": outputs.get("latency_s")}


def cost(outputs: dict) -> dict:
    """Model cost of the pipeline run in USD (list prices; the judge's own cost is not included)."""
    return {"key": "cost_usd", "score": outputs.get("cost_usd"),
            "comment": f"{outputs.get('input_tokens')} input + {outputs.get('output_tokens')} output tokens"}


def no_error(outputs: dict) -> dict:
    err = outputs.get("error")
    return {"key": "no_error", "score": int(not err), "comment": err or "Completed"}


ALL_EVALUATORS = [decision_accuracy, breach_detection, trajectory, extraction_accuracy,
                  narrative_faithfulness, latency, cost, no_error]