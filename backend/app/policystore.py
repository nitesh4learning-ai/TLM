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
        out[p["id"]] = q
    return out


def all_policies():
    pols = store.read("policy_store", None)
    if pols is None:
        pols = seed()
        store.write("policy_store", pols)
    return pols


def levels():
    return load_policies()["levels"]


EDITABLE = ["title", "folder", "stage", "level", "owner", "text", "rows", "exceptions", "cites", "appliesTo", "roles", "params", "effective", "status", "agent"]


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
    if changed:
        p["version"] = p.get("version", 1) + 1
        p.setdefault("history", []).insert(0, {"version": p["version"], "at": _now(), "by": by, "changes": ", ".join(changed)})
        if p["appliesTo"]:
            p["agent"] = p["appliesTo"][0] if p["appliesTo"][0] != ALL else "All agents"
    pols[pid] = p
    store.write("policy_store", pols)
    return p


def create(values, by="You"):
    pols = all_policies()
    prefix = values.get("prefix") or "PL"
    n = 1 + max([int(k.split("-")[-1]) for k in pols if k.startswith(prefix + "-") and k.split("-")[-1].isdigit()] or [0])
    pid = values.get("id") or f"{prefix}-{n:03d}"
    p = {"id": pid, "title": values.get("title") or "New policy", "folder": values.get("folder") or "business-rules", "stage": values.get("stage") or "Business rules",
         "agent": (values.get("appliesTo") or ["Orchestrator"])[0], "level": values.get("level") or "B", "owner": values.get("owner") or "Data governance",
         "text": values.get("text") or "", "rows": values.get("rows") or [], "exceptions": values.get("exceptions") or "", "cites": values.get("cites") or [],
         "appliesTo": values.get("appliesTo") or ["Orchestrator"], "roles": values.get("roles") or [], "params": values.get("params") or [],
         "effective": values.get("effective") or datetime.date.today().isoformat(), "status": values.get("status") or "Active", "version": 1,
         "source": values.get("source", ""), "history": [{"version": 1, "at": _now(), "by": by, "changes": "Created" + (" from " + values["source"] if values.get("source") else "")}]}
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
