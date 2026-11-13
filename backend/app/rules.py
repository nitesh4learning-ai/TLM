"""One rules engine for every business-rule policy.

A policy's rules are an ordered list. Each rule has conditions (all must hold), an outcome (attributes to set)
and who decides. The first rule whose conditions hold wins. A rule with no conditions is the default.
Values can refer to the policy's own values as ${name}.

    {"when": [{"attr": "proposed_limit", "op": "<=", "value": "${agent_limit}"}],
     "then": {"limit_approval": "Agent"}, "decidedBy": "Agent", "note": "Within agent authority"}
"""
import re

# the attributes a rule can test, shared by every agent
ATTRIBUTES = {
    "record_type": "Customer or Supplier",
    "customer_type": "e.g. Independent retail pharmacy, Hospital, Infusion center",
    "decision": "Match & merge decision: new, link, successor, review",
    "credit_tier": "A, B or C from the D&B failure score",
    "failure_class": "D&B failure score class, 1 (low risk) to 5",
    "proposed_limit": "Credit limit proposed for this customer (USD)",
    "years_trading": "Years since the business started (D&B)",
    "requested_terms": "Payment terms the customer asked for",
    "account_validation": "Account validation result: GREEN, AMBER, RED or none",
    "gpo": "Group purchasing organization named in the request",
    "has_contract": "A signed contract names the terms (true/false)",
    "has_parent_billing": "The parent confirms it pays (true/false)",
    "certificate_present": "A resale certificate was provided (true/false)",
    "certificate_holder_match": "The certificate is in the customer's own name (true/false)",
    "existing_certificate": "A valid certificate is already on file (true/false)",
    "edited_terms": "The customer edited the standard terms (true/false)",
    "license_status": "State pharmacy license status",
    "dea_status": "DEA registration status",
    "wants_controlled": "Customer will order controlled substances (true/false)",
}
OPS = ["=", "!=", "<", "<=", ">", ">=", "contains", "in", "exists", "not exists"]


def _resolve(value, params):
    if isinstance(value, str):
        m = re.fullmatch(r"\$\{(\w+)\}", value.strip())
        if m:
            return params.get(m.group(1), value)
        return re.sub(r"\$\{(\w+)\}", lambda m_: str(params.get(m_.group(1), m_.group(0))), value)
    return value


def _num(x):
    try:
        return float(str(x).replace(",", "").replace("$", ""))
    except (TypeError, ValueError):
        return None


def _bool(x):
    if isinstance(x, bool):
        return x
    if isinstance(x, str) and x.strip().lower() in ("true", "yes", "y"):
        return True
    if isinstance(x, str) and x.strip().lower() in ("false", "no", "n"):
        return False
    return x


def _norm(x):
    return str(x).replace(" ", "").lower() if x is not None else ""


def holds(cond, ctx, params):
    op = cond.get("op", "=")
    have = ctx.get(cond.get("attr"))
    want = _resolve(cond.get("value"), params)
    if op == "exists":
        return have not in (None, "", False)
    if op == "not exists":
        return have in (None, "", False)
    if have is None:
        return False
    if op in ("<", "<=", ">", ">="):
        a, b = _num(have), _num(want)
        if a is None or b is None:
            return False
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
    if op == "contains":
        return _norm(want) in _norm(have)
    if op == "in":
        return _norm(have) in [_norm(v) for v in (want if isinstance(want, list) else str(want).split(","))]
    hb, wb = _bool(have), _bool(want)
    if isinstance(hb, bool) or isinstance(wb, bool):
        eq = hb == wb
    else:
        a, b = _num(have), _num(want)
        eq = (a == b) if a is not None and b is not None else _norm(have) == _norm(want)
    return eq if op == "=" else not eq


def describe(rule, params=None):
    params = params or {}
    if not rule.get("when"):
        return "Otherwise"
    parts = []
    for c in rule["when"]:
        v = c.get("value")
        shown = f"{v} ({_resolve(v, params)})" if isinstance(v, str) and "${" in v and params else v
        parts.append(f"{c.get('attr')} {c.get('op', '=')}" + ("" if c.get("op") in ("exists", "not exists") else f" {shown}"))
    return " and ".join(parts)


def evaluate(policy, ctx):
    """Returns {matched, index, rule, outcome, decidedBy, condition, note} or matched=False when no rule applies."""
    params = {p["key"]: p["value"] for p in policy.get("params", [])}
    for i, rule in enumerate(policy.get("rules") or []):
        if all(holds(c, ctx, params) for c in rule.get("when", [])):
            outcome = {k: _resolve(v, params) for k, v in (rule.get("then") or {}).items()}
            return {"matched": True, "index": i, "rule": rule, "outcome": outcome, "decidedBy": rule.get("decidedBy") or "Agent",
                    "condition": describe(rule, params), "note": rule.get("note", "")}
    return {"matched": False, "index": None, "rule": None, "outcome": {}, "decidedBy": "Data steward", "condition": "No rule matched", "note": ""}


def run_tests(policy):
    out = []
    for t in policy.get("testCases") or []:
        r = evaluate(policy, t.get("inputs", {}))
        exp = t.get("expect", {})
        got = dict(r["outcome"], decidedBy=r["decidedBy"])
        ok = all(_norm(got.get(k)) == _norm(_resolve(v, {p["key"]: p["value"] for p in policy.get("params", [])})) for k, v in exp.items())
        out.append({"name": t.get("name", ""), "passed": ok, "expected": exp, "got": got, "rule": r["condition"]})
    return out
