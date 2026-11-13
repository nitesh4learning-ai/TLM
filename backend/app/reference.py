"""Loads reference data (source systems, D&B, LexisNexis, account/address validation, hierarchy, policies)."""
import json
import os
import re
from difflib import SequenceMatcher

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA = os.path.join(REPO, "data")


def load(rel):
    with open(os.path.join(DATA, rel)) as f:
        return json.load(f)


def load_policies():
    with open(os.path.join(REPO, "policies", "policies.json")) as f:
        return json.load(f)


SAP = load("sources/sap/customers.json")["records"]
LEGACY = load("sources/legacy/customers.json")["records"]
HIERARCHY = load("hierarchy/brazos-health-system.json")
HIERARCHY.setdefault("key", "brazos")
HIERARCHY.setdefault("name", HIERARCHY["nodes"][0]["name"])
FAMILIES = {"brazos": HIERARCHY}
for _f in sorted(os.listdir(os.path.join(DATA, "hierarchy"))):
    if _f.endswith(".json") and _f != "brazos-health-system.json":
        _h = load("hierarchy/" + _f)
        FAMILIES[_h["key"]] = _h
LEXIS = {r["entity"].lower(): r for r in load("lexisnexis/business-checks.json")["records"]}
AVS_ACCT = {r["entity"].lower(): r for r in load("avs/account-validation.json")["records"]}
AVS_ADDR = load("avs/address-validation.json")["records"]

# D&B identity resolution results for parties that are not in the hierarchy file
DNB_EXTRA = {
    "lakeside community pharmacy": {"duns": "08-447-3921", "primaryName": "Lakeside Community Pharmacy, LLC", "parent": "Lakeside Rx Holdings, LLC",
                                    "globalUltimate": "Lakeside Rx Holdings, LLC", "naics": "456110 · Pharmacies and drug retailers", "startDate": "2019",
                                    "employees": 18, "failureScoreClass": 3, "confidenceCode": 9, "ownershipChangeDate": None},
    "cedar park family pharmacy": {"duns": "61-203-4471", "primaryName": "Cedar Park Family Pharmacy, LLC", "parent": None, "globalUltimate": None,
                                   "naics": "456110 · Pharmacies and drug retailers", "startDate": "2011", "employees": 22, "failureScoreClass": 2,
                                   "confidenceCode": 10, "ownershipChangeDate": None},
    "westbrook infusion": {"duns": "07-118-6630", "primaryName": "Westbrook Infusion Partners LP", "parent": "Northstar Infusion Holdings",
                           "globalUltimate": "Northstar Infusion Holdings", "naics": "621498 · Outpatient care centers", "startDate": "2014",
                           "employees": 64, "failureScoreClass": 2, "confidenceCode": 9, "ownershipChangeDate": "2026-09-02",
                           "priorOwner": "Westbrook Infusion Center LLC"},
}
if os.path.exists(os.path.join(DATA, "dnb", "scenario-companies.json")):
    for _c in load("dnb/scenario-companies.json")["companies"]:
        DNB_EXTRA.setdefault(_c["primaryName"].lower(), {k: v for k, v in _c.items() if k != "key"})
for node in [n for fam in FAMILIES.values() for n in fam["nodes"]]:
    if node.get("duns"):
        DNB_EXTRA.setdefault(node["name"].lower(), {"duns": node["duns"], "primaryName": node["name"], "parent": None,
                                                    "globalUltimate": next(f for f in FAMILIES.values() if node in f["nodes"])["nodes"][0]["name"], "naics": "622110 · General medical and surgical hospitals",
                                                    "startDate": "1998", "employees": 400, "failureScoreClass": 2, "confidenceCode": 9,
                                                    "ownershipChangeDate": None})

LEXIS.setdefault("cedar park family pharmacy llc", {"entity": "Cedar Park Family Pharmacy LLC", "checks": {
    "ofac": {"result": "clear"}, "oig_leie": {"result": "clear"}, "sam_gov": {"result": "clear"},
    "stateLicense": {"number": "TX-PH-337905", "status": "Active", "expires": "2027-03-31"},
    "dea": {"number": "FC2201846", "status": "Active", "expires": "2027-03-31", "schedules": ["II", "III", "IV", "V"]}}})
LEXIS.setdefault("westbrook infusion partners lp", {"entity": "Westbrook Infusion Partners LP", "checks": {
    "ofac": {"result": "clear"}, "oig_leie": {"result": "clear"}, "sam_gov": {"result": "clear"},
    "stateLicense": {"number": "TX-PH-552018", "status": "Active", "expires": "2027-08-31"},
    "dea": {"number": "BW7742105", "status": "Active", "expires": "2027-08-31", "schedules": ["II", "III", "IV", "V"]}}})

STOP = {"llc", "inc", "lp", "ltd", "co", "corp", "the", "of"}
ABBR = {"pk": "park", "fam": "family", "phcy": "pharmacy", "pharm": "pharmacy", "ctr": "center", "e": "east", "w": "west",
        "s": "south", "n": "north", "blvd": "boulevard", "ave": "avenue", "ste": "suite", "st": "street", "dr": "drive"}


def norm(text):
    toks = re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).split()
    return " ".join(ABBR.get(t, t) for t in toks if t not in STOP)


def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


GENERIC = {"pharmacy", "drug", "mart", "rx"}


def name_sim(a, b):
    seq = sim(a, b)
    ta = set(norm(a).split()) - GENERIC
    tb = set(norm(b).split()) - GENERIC
    jac = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
    return 0.5 * seq + 0.5 * jac


def addr_sim(a, b):
    """Street similarity that requires the same house number and the same ZIP or city."""
    na, nb = norm(a).split(), norm(b).split()
    if not na or not nb:
        return 0.0
    ha, hb = na[0] if na[0].isdigit() else None, nb[0] if nb[0].isdigit() else None
    seq = SequenceMatcher(None, norm(street_of(a)), norm(street_of(b))).ratio()
    if ha and hb and ha != hb:
        return 0.3 * seq
    za = re.findall(r"\b\d{5}\b", a or "")
    zb = re.findall(r"\b\d{5}\b", b or "")
    if za and zb and za[-1] != zb[-1]:
        return 0.5 * seq
    return seq


def street_of(addr):
    return (addr or "").split(",")[0]


def dnb_lookup(name):
    n = norm(name)
    best, score = None, 0.0
    for key, rec in DNB_EXTRA.items():
        s = SequenceMatcher(None, n, norm(key)).ratio()
        if norm(key) in n:
            s = max(s, 0.95)
        if s > score:
            best, score = rec, s
    return best if score >= 0.75 else None


def lexis_lookup(name):
    n = norm(name)
    for key, rec in LEXIS.items():
        if norm(key) == n or SequenceMatcher(None, n, norm(key)).ratio() > 0.9:
            return rec
    return None


def avs_account(name):
    n = norm(name)
    for key, rec in AVS_ACCT.items():
        if SequenceMatcher(None, n, norm(key)).ratio() > 0.85:
            return rec
    return None


def avs_address(addr):
    s = norm(street_of(addr))
    for rec in AVS_ADDR:
        if SequenceMatcher(None, s, norm(street_of(rec["input"]))).ratio() > 0.85:
            return rec
    return None
