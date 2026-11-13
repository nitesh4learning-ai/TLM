"""The runtime policy store.

Policies are editable while the app runs. Every save is published at once and gets a new version number;
agents read the current set at the start of each request and record which version of each policy they used.
A policy applies to the agents listed in `appliesTo` (or "All agents") and may name people's roles.
"""
import copy
import datetime

from . import store
from .reference import load_policies

ALL = "All agents"
AGENT_NAMES = ["Orchestrator", "Intake", "Search before create", "Match & merge", "Enrichment", "Validation",
               "Legal", "Procurement", "Credit", "Tax", "Steward copilot", "Lifecycle monitor", "Contextual outreach"]

# the values the agents actually run; the conditions table documents them for people
PARAMS = {
    "MM-002": [("link_at", 0.95, "Link to an existing record at or above this score"), ("review_from", 0.80, "Steward reviews from this score up to the link score")],
    "MM-007a": [("ownership_window_days", 365, "Ownership change counts if D&B reports it within this many days"),
                ("deactivate_after_days", 30, "Days before the old record is deactivated if it has no open orders")],
    "AG-002": [("intake_auto", 0.95, "Intake field confidence that needs no confirmation"), ("intake_steward_below", 0.75, "Below this, a steward checks the field"),
               ("dnb_accept", 8, "D&B confidence code accepted without review"), ("exclusion_clear_below", 0.80, "Exclusion-list name match below this is cleared")],
    "BR-CR-001": [("agent_limit", 50000, "Credit limit the agent approves on its own (USD)"), ("manager_limit", 250000, "Above this, the BU finance director also approves (USD)")],
    "BR-PT-001": [("default_terms", "Net 30", "Terms for any approved customer"), ("tier_a_terms", "Net 45", "Longer terms allowed for credit tier A"),
                  ("tier_a_max_limit", 50000, "Tier A terms only up to this credit limit (USD)")],
    "BR-TX-001": [("certificate_name_match", 0.9, "Certificate holder must match the legal name at least this closely")],
    "RG-CS-001": [("lapse_warning_days", 60, "Warn when a license or DEA registration lapses within this many days")],
    "BR-PM-001": [("wire_above", 250000, "Single payments above this go by wire (USD)")],
}
ROLES = {"MM-002": ["Data steward"], "MM-007a": ["Credit manager"], "BR-PT-001": ["Credit manager", "BU finance director"],
         "BR-PM-001": ["Data steward", "Treasury"], "BR-CR-001": ["Credit manager", "BU finance director"], "BR-TX-001": ["Tax specialist"],
         "BR-LG-001": ["Legal counsel"], "RG-CS-001": ["Regulatory compliance", "Data steward"], "BPO-001": ["BPO", "Category manager"],
         "AG-001": ["Data governance"], "AG-002": ["Data steward"], "BR-PR-001": ["Pricing analyst"], "BR-PF-001": ["Data steward"]}
UNIVERSAL = {"AG-001", "AG-002", "AG-003"}
APPLIES = {"MM-002": ["Search before create", "Match & merge"], "SV-001": ["Match & merge", "Enrichment"],
           "RG-CS-001": ["Legal", "Validation"], "BR-PM-001": ["Credit", "Validation"], "MM-007a": ["Match & merge", "Credit", "Orchestrator"]}


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def seed():
    base = load_policies()
    out = {}
    for p in base["policies"]:
        q = copy.deepcopy(p)
        q["appliesTo"] = [ALL] if p["id"] in UNIVERSAL else APPLIES.get(p["id"], [p["agent"]])
        q["roles"] = ROLES.get(p["id"], [])
        q["params"] = [{"key": k, "value": v, "help": h} for k, v, h in PARAMS.get(p["id"], [])]
        q["effective"] = "2026-11-01"
        q["status"] = "Active"
        q["version"] = 1
        q["history"] = [{"version": 1, "at": "2026-11-01 09:00", "by": "Data governance", "changes": "Published"}]
        out[p["id"]] = upgrade(q)
    return out


def all_policies():
    pols = store.read("policy_store", None)
    if pols is None:
        pols = seed()
        store.write("policy_store", pols)
    elif any(p.get("schema") != 2 for p in pols.values()):
        pols = {k: upgrade(p) for k, p in pols.items()}
        store.write("policy_store", pols)
    return pols


def levels():
    return load_policies()["levels"]


EDITABLE = ["title", "folder", "stage", "level", "owner", "text", "rows", "exceptions", "cites", "appliesTo", "roles", "params", "effective", "status", "agent",
            "steward", "effectiveTo", "recordTypes", "regions", "triggers", "inputs", "rules", "approverRole", "escalation", "slaHours", "priority",
            "complianceFloor", "citationRequired", "testCases", "fieldSources", "source", "engine"]


def save(pid, values, by="You"):
    pols = all_policies()
    p = pols.get(pid)
    if p is None:
        raise KeyError(pid)
    changed = []
    for k in EDITABLE:
        if k in values and values[k] is not None and values[k] != p.get(k):
            p[k] = values[k]
            changed.append(k)
    if values.get("status") is None and p.get("status") == "Draft" and values.get("publish"):
        p["status"] = "Active"; changed.append("status")
    if p.get("status") == "Active" and completeness(p)["missing"]:
        raise ValueError("Cannot activate: fill in " + ", ".join(completeness(p)["missing"]))
    if "fieldSources" not in values and changed:
        # a person edited these fields, so they are no longer waiting for governance input
        fs = p.get("fieldSources") or {}
        for k in changed:
            if k in fs:
                fs[k] = {**fs[k], "from": "edited", "by": by}
        p["fieldSources"] = fs
    if changed:
        p["version"] = p.get("version", 1) + 1
        p.setdefault("history", []).insert(0, {"version": p["version"], "at": _now(), "by": by, "changes": ", ".join(changed)})
        if p.get("appliesTo"):
            p["agent"] = p["appliesTo"][0] if p["appliesTo"][0] != ALL else "All agents"
    pols[pid] = p
    store.write("policy_store", pols)
    return p


def create(values, by="You"):
    pols = all_policies()
    prefix = values.get("prefix") or "PL"
    n = 1 + max([int(k.split("-")[-1]) for k in pols if k.startswith(prefix + "-") and k.split("-")[-1].isdigit()] or [0])
    pid = values.get("id") or f"{prefix}-{n:03d}"
    blank = bool(values.get("fieldSources"))  # from a document: leave unknown fields empty for governance to fill
    p = {"id": pid, "title": values.get("title") or "New policy", "folder": values.get("folder") or "business-rules", "stage": values.get("stage") or "Business rules",
         "agent": (values.get("appliesTo") or ["—"])[0], "level": values.get("level") or "B", "owner": values.get("owner") or ("" if blank else "Data governance"),
         "text": values.get("text") or "", "rows": values.get("rows") or [], "exceptions": values.get("exceptions") or "", "cites": values.get("cites") or [],
         "appliesTo": values.get("appliesTo") or ([] if blank else ["Orchestrator"]), "roles": values.get("roles") or [], "params": values.get("params") or [],
         "effective": values.get("effective") or ("" if blank else datetime.date.today().isoformat()), "status": values.get("status") or "Active", "version": 1,
         "source": values.get("source", ""), "history": [{"version": 1, "at": _now(), "by": by, "changes": "Created" + (" from " + values["source"] if values.get("source") else "")}]}
    for k in ("steward", "effectiveTo", "recordTypes", "regions", "triggers", "inputs", "rules", "approverRole", "escalation", "slaHours", "priority",
              "complianceFloor", "citationRequired", "testCases", "fieldSources", "engine"):
        if k in values:
            p[k] = values[k]
    p = upgrade(p)
    pols[pid] = p
    store.write("policy_store", pols)
    return p


def for_agent(agent):
    """Policies an agent reads: the ones assigned to it plus the universal ones. Drafts and retired policies are skipped."""
    return [p for p in all_policies().values() if p.get("status") == "Active" and (ALL in p.get("appliesTo", []) or agent in p.get("appliesTo", []))]


class Runtime:
    """A snapshot of the active policy set, taken at the start of a request."""

    def __init__(self):
        self.pols = {k: p for k, p in all_policies().items() if p.get("status") == "Active"}

    def assigned(self, agent, pid):
        p = self.pols.get(pid)
        return bool(p) and (ALL in p.get("appliesTo", []) or agent in p.get("appliesTo", []))

    def param(self, pid, key, default):
        p = self.pols.get(pid)
        for x in (p or {}).get("params", []):
            if x["key"] == key:
                v = x["value"]
                if isinstance(default, (int, float)) and not isinstance(default, bool):
                    try:
                        return type(default)(float(v)) if isinstance(default, int) else float(v)
                    except (TypeError, ValueError):
                        return default
                return v
        return default

    def level(self, pid):
        return (self.pols.get(pid) or {}).get("level", "B")

    def gate(self, pid, needs_person):
        """Autonomy matrix: A = the agent decides, B = a person when the rule says so, H = always a person."""
        lv = self.level(pid)
        return False if lv == "A" else True if lv == "H" else bool(needs_person)

    def version(self, pid):
        p = self.pols.get(pid)
        return p.get("version") if p else None

    def roles(self, pid):
        return (self.pols.get(pid) or {}).get("roles", [])


# ------------------------------------------------------------------ common policy framework (schema v2)
def C(attr, op, value=None):
    return {"attr": attr, "op": op, "value": value}


def R(when, then, decided="Agent", note=""):
    return {"when": when, "then": then, "decidedBy": decided, "note": note}


ENGINE_RULES = {
    "BR-CR-001": [R([C("proposed_limit", "<=", "${agent_limit}")], {"limit_approval": "Agent"}, "Agent", "Within agent authority"),
                  R([C("proposed_limit", "<=", "${manager_limit}")], {"limit_approval": "Credit manager"}, "Credit manager", "Above agent authority"),
                  R([], {"limit_approval": "Credit manager and BU finance director"}, "Credit manager and BU finance director", "Above manager limit")],
    "BR-PT-001": [R([C("requested_terms", "=", "${tier_a_terms}"), C("credit_tier", "=", "A"), C("proposed_limit", "<=", "${tier_a_max_limit}")],
                    {"terms": "${tier_a_terms}"}, "Agent", "Tier A, within the limit for longer terms"),
                  R([C("years_trading", "<", 1)], {"terms": "Prepay or Net 15"}, "Credit manager", "Business under 12 months old"),
                  R([], {"terms": "${default_terms}"}, "Agent", "Default terms")],
    "BR-PM-001": [R([C("account_validation", "=", "GREEN")], {"payment_method": "ACH"}, "Agent", "Bank account validated"),
                  R([C("account_validation", "=", "AMBER")], {"payment_method": "ACH after steward confirms"}, "Data steward", "Partial name match on the bank account"),
                  R([], {"payment_method": "Check"}, "Agent", "No validated bank account")],
    "BR-TX-001": [R([C("existing_certificate", "=", True)], {"tax_class": "Exempt for resale"}, "Agent", "Valid certificate already on file"),
                  R([C("certificate_present", "=", False)], {"tax_class": "Taxable"}, "Tax specialist", "Certificate missing; collect it"),
                  R([C("certificate_holder_match", "=", False)], {"tax_class": "Taxable"}, "Tax specialist", "Certificate is in another name"),
                  R([], {"tax_class": "Exempt for resale"}, "Agent", "Valid certificate in the customer's name")],
    "BR-PR-001": [R([C("decision", "=", "successor")], {"pricing_group": "Carried from the site contract"}, "Agent", "Contract carried to the new owner"),
                  R([C("gpo", "exists")], {"pricing_group": "GPO tier"}, "Agent", "GPO membership"),
                  R([C("customer_type", "contains", "hospital")], {"pricing_group": "Group named in the IDN contract"}, "Agent", "Hospital or health system"),
                  R([], {"pricing_group": "Independent retail"}, "Agent", "No contract")],
    "BR-PF-001": [R([C("has_parent_billing", "=", True)], {"partners": "Bill-to and payer at the parent"}, "Agent", "Parent confirms billing"),
                  R([], {"partners": "Sold-to = bill-to = payer; 1 ship-to"}, "Agent", "Single site")],
    "BR-LG-001": [R([C("edited_terms", "=", True)], {"terms_of_sale": "Hold for review"}, "Legal counsel", "Customer edited the terms"),
                  R([], {"terms_of_sale": "Accepted"}, "Agent", "Standard terms accepted without edits")],
    "RG-CS-001": [R([C("license_status", "!=", "Active")], {"ordering": "Hold; no ordering"}, "Regulatory compliance", "License not active"),
                  R([C("wants_controlled", "=", True), C("dea_status", "!=", "Active")], {"ordering": "Controlled ordering off"}, "Regulatory compliance", "DEA not active"),
                  R([C("wants_controlled", "=", True)], {"ordering": "Controlled ordering on"}, "Agent", "License and DEA active"),
                  R([], {"ordering": "Non-controlled only"}, "Agent", "License active; no controlled substances requested")],
}

TESTS = {
    "BR-CR-001": [{"name": "Small limit", "inputs": {"proposed_limit": 40000}, "expect": {"decidedBy": "Agent"}},
                  {"name": "Mid limit", "inputs": {"proposed_limit": 80000}, "expect": {"decidedBy": "Credit manager"}},
                  {"name": "Large limit", "inputs": {"proposed_limit": 400000}, "expect": {"decidedBy": "Credit manager and BU finance director"}}],
    "BR-PT-001": [{"name": "Tier B asks for Net 45", "inputs": {"requested_terms": "Net 45", "credit_tier": "B", "proposed_limit": 80000, "years_trading": 7}, "expect": {"terms": "${default_terms}"}},
                  {"name": "Tier A within limit", "inputs": {"requested_terms": "Net 45", "credit_tier": "A", "proposed_limit": 40000, "years_trading": 7}, "expect": {"terms": "${tier_a_terms}"}},
                  {"name": "New business", "inputs": {"years_trading": 0.5}, "expect": {"decidedBy": "Credit manager"}}],
    "BR-PM-001": [{"name": "Validated account", "inputs": {"account_validation": "GREEN"}, "expect": {"payment_method": "ACH"}},
                  {"name": "Partial name match", "inputs": {"account_validation": "AMBER"}, "expect": {"decidedBy": "Data steward"}}],
    "BR-TX-001": [{"name": "Certificate in another name", "inputs": {"certificate_present": True, "certificate_holder_match": False}, "expect": {"tax_class": "Taxable"}},
                  {"name": "Valid certificate", "inputs": {"certificate_present": True, "certificate_holder_match": True}, "expect": {"tax_class": "Exempt for resale"}}],
    "BR-PR-001": [{"name": "Independent pharmacy", "inputs": {"customer_type": "Independent retail pharmacy"}, "expect": {"pricing_group": "Independent retail"}}],
    "RG-CS-001": [{"name": "DEA lapsed", "inputs": {"license_status": "Active", "wants_controlled": True, "dea_status": "Expired"}, "expect": {"decidedBy": "Regulatory compliance"}}],
}

INPUTS = {
    "BR-CR-001": [("proposed_limit", "Credit agent (D&B score, expected volume)")],
    "BR-PT-001": [("requested_terms", "Intake"), ("credit_tier", "D&B"), ("proposed_limit", "Credit agent"), ("years_trading", "D&B")],
    "BR-PM-001": [("account_validation", "Account validation (AVS)")],
    "BR-TX-001": [("certificate_present", "Intake"), ("certificate_holder_match", "Intake"), ("existing_certificate", "Business ready record")],
    "BR-PR-001": [("decision", "Match & merge"), ("gpo", "Intake"), ("customer_type", "Intake")],
    "BR-PF-001": [("has_parent_billing", "D&B family tree")],
    "BR-LG-001": [("edited_terms", "Intake")],
    "RG-CS-001": [("license_status", "State Board of Pharmacy"), ("dea_status", "DEA registration"), ("wants_controlled", "Intake")],
    "MM-002": [("match score", "Search before create")], "MM-007a": [("match score", "Search before create"), ("ownership change date", "D&B")],
    "SV-001": [("source attributes", "All sources")], "AG-002": [("confidence scores", "Every agent")],
}

REQUIRED = ["title", "owner", "appliesTo", "level", "text", "effective"]
FORM_DEFAULTS = {"steward": "", "effectiveTo": "", "recordTypes": ["Customer"], "regions": ["US"], "triggers": ["Create", "Change"],
                 "inputs": [], "rules": [], "approverRole": "", "escalation": "", "slaHours": 24, "priority": 50,
                 "complianceFloor": False, "citationRequired": True, "testCases": [], "fieldSources": {}, "schema": 2, "engine": False}


def upgrade(p):
    """Adds the common-framework fields to a policy without touching anything already edited."""
    for k, v in FORM_DEFAULTS.items():
        p.setdefault(k, copy.deepcopy(v))
    pid = p["id"]
    if not p.get("rules") and pid in ENGINE_RULES:
        p["rules"] = copy.deepcopy(ENGINE_RULES[pid])
    if pid in ENGINE_RULES:
        p["engine"] = True
    if not p.get("testCases") and pid in TESTS:
        p["testCases"] = copy.deepcopy(TESTS[pid])
    if not p.get("inputs") and pid in INPUTS:
        p["inputs"] = [{"attribute": a, "source": s} for a, s in INPUTS[pid]]
    if not p.get("approverRole"):
        p["approverRole"] = (p.get("roles") or [""])[0]
    if pid in ("RG-CS-001", "AG-001"):
        p["complianceFloor"] = True
        p["priority"] = 10
    if pid.startswith("BPO"):
        p["recordTypes"] = ["Supplier"]
    p["schema"] = 2
    return p


def completeness(p):
    missing = [k for k in REQUIRED if not p.get(k)]
    if not (p.get("rules") or p.get("rows") or p.get("params")):
        missing.append("rules")
    needs = [k for k, v in (p.get("fieldSources") or {}).items() if v.get("from") == "governance"]
    total = len(REQUIRED) + 1
    return {"score": round(100 * (total - len(missing)) / total), "missing": missing, "needsGovernance": needs}
