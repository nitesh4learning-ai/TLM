"""A small JSON file store for requests, Business ready records, policy drafts and agent setting changes."""
import json
import os
import threading
from .reference import SAP, LEGACY, HIERARCHY

STORE_DIR = os.environ.get("TLM_STORE_DIR", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "store")))
_lock = threading.Lock()


def _path(name):
    os.makedirs(STORE_DIR, exist_ok=True)
    return os.path.join(STORE_DIR, name + ".json")


def read(name, default):
    p = _path(name)
    if not os.path.exists(p):
        return default
    with open(p) as f:
        return json.load(f)


def write(name, value):
    with _lock:
        tmp = _path(name) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(value, f, indent=2)
        os.replace(tmp, _path(name))


def _sap(kunnr):
    return next(r for r in SAP if r["KUNNR"] == kunnr)


def _leg(lid):
    return next(r for r in LEGACY if r["legacyId"] == lid)


def xref_sap(r):
    return {"system": "SAP S/4HANA", "id": r["KUNNR"], "name": r["NAME1"], "address": f"{r['STRAS']}, {r['ORT01']}, {r['REGIO']} {r['PSTLZ']}",
            "taxId": r["STCD1"], "paymentTerms": r["ZTERM"], "creditLimit": r["KLIMK"], "accountGroup": r["KTOKD"], "salesOrg": r["VKORG"]}


def xref_leg(r):
    return {"system": r["system"], "id": r["legacyId"], "name": r["customerName"], "address": r["addressLine"], "taxId": r["taxRef"],
            "paymentTerms": r["paymentTerms"], "creditLimit": None, "accountGroup": None, "salesOrg": None}


def seed_records():
    cedar = {"id": "BRR-0004417", "status": "Active", "legalName": "Cedar Park Family Pharmacy, LLC", "dba": None,
             "duns": "61-203-4471", "address": "1200 E WHITESTONE BLVD, CEDAR PARK TX 78613-3047", "taxId": _sap("0001004417")["STCD1"],
             "type": "Independent retail pharmacy", "parent": None,
             "salesAreas": [{"area": "Pharma · US01", "paymentTerms": "Net 30", "creditLimit": 50000, "paymentMethod": "ACH",
                             "pricingGroup": "Independent retail", "taxClass": "Exempt for resale", "controlled": "CII–CV on"}],
             "winners": {"legalName": ["D&B", "SV-001"], "address": ["Address validation", "SV-001"], "taxId": ["SAP 0001004417", "SV-001"],
                         "paymentTerms": ["SAP 0001004417", "BR-PT-001"], "creditLimit": ["SAP 0001004417", "BR-CR-001"]},
             "crossReferences": [xref_sap(_sap("0001004417")), xref_sap(_sap("0001004418")), xref_sap(_sap("0001009902")),
                                 xref_leg(_leg("ORA-88213")), xref_leg(_leg("AS4-30771"))],
             "history": [{"when": "2025-02-11", "change": "AS/400 AS4-30771 merged", "by": "J. Ortiz, data steward"}]}
    west = {"id": "BRR-0003388", "status": "Active", "legalName": "Westbrook Infusion Center LLC", "dba": None, "duns": "07-118-6630",
            "address": "4500 W PARK BLVD STE 120, PLANO TX 75093-2210", "taxId": _sap("0001003388")["STCD1"], "type": "Infusion center",
            "parent": None, "salesAreas": [{"area": "Specialty · US02", "paymentTerms": "Net 30", "creditLimit": 120000, "paymentMethod": "ACH",
                                            "pricingGroup": "IDN Tier 2", "taxClass": "Exempt for resale", "controlled": "CII–CV on"}],
            "winners": {}, "crossReferences": [xref_sap(_sap("0001003388")), xref_leg(_leg("ORA-55102"))], "history": []}
    lake2 = {"id": "BRR-0000428", "status": "Active", "legalName": "Lakeside Pharmacy #2", "dba": None, "duns": None,
             "address": "310 N BROADWAY AVE, TYLER TX 75702", "taxId": _sap("0000042871")["STCD1"], "type": "Independent retail pharmacy",
             "parent": None, "salesAreas": [{"area": "Pharma · US01", "paymentTerms": "Net 30", "creditLimit": 50000}], "winners": {},
             "crossReferences": [xref_sap(_sap("0000042871"))], "history": []}
    recs = {r["id"]: r for r in (cedar, west, lake2)}
    for i, n in enumerate(HIERARCHY["nodes"]):
        if n["level"] in (1, 2):
            rid = f"BRR-{3000 + i:07d}"
            recs[rid] = {"id": rid, "status": n["status"] if n["status"] != "Proposed" else "Proposed", "legalName": n["name"], "dba": None,
                         "duns": n["duns"], "address": n.get("address") or f"{n['city']}, {n['state']}", "taxId": n.get("tax_id"),
                         "type": n["kind"], "parent": n["parent"], "hierarchyNode": n["id"], "salesAreas": [], "winners": {},
                         "crossReferences": [], "history": []}
    return recs


def records():
    recs = read("records", None)
    if recs is None:
        recs = seed_records()
        write("records", recs)
    return recs


def save_record(rec):
    recs = records()
    recs[rec["id"]] = rec
    write("records", recs)


def next_id(prefix, existing, start):
    nums = [int(k.split("-")[1]) for k in existing if k.startswith(prefix)]
    return f"{prefix}-{max(nums + [start]) + 1:07d}" if prefix == "BRR" else f"{prefix}-{max(nums + [start]) + 1}"


def requests():
    return read("requests", {})


def save_request(req):
    reqs = requests()
    reqs[req["id"]] = req
    write("requests", reqs)
