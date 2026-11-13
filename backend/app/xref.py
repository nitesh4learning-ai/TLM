"""Cross-reference (XREF) layer under every Business ready record, in the style of Informatica MDM.

A record keeps every contributing source row: SAP, legacy systems, D&B, address validation, LexisNexis, the intake form,
and writes by the operational agents (source = agent + the policy that authorised it). The record's attribute values
are computed from those rows by the survivorship rules in policy SV-001, which is editable in Master data policies.
"""
import copy
import datetime

ATTRS = [("legalName", "Legal name"), ("dba", "DBA"), ("address", "Address"), ("taxId", "Tax ID"), ("duns", "DUNS"), ("parent", "Parent"),
         ("paymentTerms", "Payment terms"), ("creditLimit", "Credit limit"), ("paymentMethod", "Payment method"), ("pricingGroup", "Pricing group"),
         ("taxClass", "Tax class"), ("partners", "Partner functions")]
LABEL = dict(ATTRS)
EXTENDED = {"paymentTerms", "creditLimit", "paymentMethod", "pricingGroup", "taxClass", "partners"}

DEFAULT_SURVIVORSHIP = [
    {"attribute": "legalName", "method": "source priority", "order": ["D&B", "SAP S/4HANA", "Intake", "Oracle EBS", "AS/400 Order Entry"]},
    {"attribute": "dba", "method": "most recent", "order": ["Intake", "SAP S/4HANA"]},
    {"attribute": "address", "method": "source priority", "order": ["Address validation", "SAP S/4HANA", "Intake", "Oracle EBS", "AS/400 Order Entry"]},
    {"attribute": "taxId", "method": "source priority", "order": ["Intake", "SAP S/4HANA", "Oracle EBS", "AS/400 Order Entry"]},
    {"attribute": "duns", "method": "source priority", "order": ["D&B"]},
    {"attribute": "parent", "method": "source priority", "order": ["D&B"]},
    {"attribute": "paymentTerms", "method": "agent decision", "order": ["SAP S/4HANA", "Oracle EBS", "AS/400 Order Entry"]},
    {"attribute": "creditLimit", "method": "agent decision", "order": ["SAP S/4HANA"]},
    {"attribute": "paymentMethod", "method": "agent decision", "order": ["SAP S/4HANA"]},
    {"attribute": "pricingGroup", "method": "agent decision", "order": ["SAP S/4HANA"]},
    {"attribute": "taxClass", "method": "agent decision", "order": ["SAP S/4HANA"]},
    {"attribute": "partners", "method": "agent decision", "order": ["SAP S/4HANA"]},
]
DEFAULT_TRUST = [("trust_dnb", 0.95, "Trust score for D&B"), ("trust_address_validation", 0.95, "Trust score for address validation"),
                 ("trust_sap", 0.90, "Trust score for SAP S/4HANA"), ("trust_intake", 0.80, "Trust score for the intake form"),
                 ("trust_oracle_ebs", 0.60, "Trust score for Oracle EBS"), ("trust_as400", 0.40, "Trust score for AS/400 Order Entry")]
METHODS = ["source priority", "most recent", "highest trust", "agent decision"]
TRUST_KEY = {"D&B": "trust_dnb", "Address validation": "trust_address_validation", "SAP S/4HANA": "trust_sap", "Intake": "trust_intake",
             "Oracle EBS": "trust_oracle_ebs", "AS/400 Order Entry": "trust_as400"}


def today():
    return datetime.date.today().isoformat()


def row(system, key, attrs, kind="source", load=None, policy=None, by=None):
    attrs = {k: v for k, v in attrs.items() if v not in (None, "", "—")}
    return {"xid": f"{system}:{key}", "system": system, "sourceKey": key, "loadDate": load or today(), "kind": kind,
            "policy": policy, "by": by, "attrs": attrs}


def from_xref(x):
    """Old cross-reference format (system, id, name, address, taxId, paymentTerms, creditLimit) to an XREF row."""
    terms = {"NT30": "Net 30", "N30": "Net 30", "NET 30": "Net 30", "NT45": "Net 45", "N45": "Net 45"}.get(str(x.get("paymentTerms") or "").upper(), x.get("paymentTerms"))
    return row(x["system"], x["id"], {"legalName": x.get("name"), "address": x.get("address"), "taxId": x.get("taxId"), "paymentTerms": terms,
                                      "creditLimit": x.get("creditLimit") or None}, load=x.get("loadDate"))


def survive(rec, policy):
    """Applies the survivorship rules to the record's XREF rows; sets the winning values and records why each won."""
    rules = {r["attribute"]: r for r in (policy or {}).get("survivorship") or DEFAULT_SURVIVORSHIP}
    params = {p["key"]: p["value"] for p in (policy or {}).get("params", [])}
    pid = (policy or {}).get("id", "SV-001")
    rows = rec.get("xrefs") or []
    winners = {}
    for attr, label in ATTRS:
        cands = [r for r in rows if r["attrs"].get(attr) not in (None, "")]
        if not cands:
            continue
        rule = rules.get(attr) or {"method": "source priority", "order": []}
        order = rule.get("order") or []
        method = rule.get("method", "source priority")
        win, reason = None, ""
        if method == "agent decision":
            agents = sorted([r for r in cands if r["kind"] == "agent"], key=lambda r: r["loadDate"])
            if agents:
                win = agents[-1]
                reason = f"Agent decision wins: {win['system']} under {win.get('policy')}"
            method = "source priority"
        if not win and method == "most recent":
            win = max(cands, key=lambda r: r["loadDate"])
            reason = f"Most recent wins ({win['loadDate']})"
        if not win and method == "highest trust":
            win = max(cands, key=lambda r: float(params.get(TRUST_KEY.get(r["system"], ""), 0.5)))
            reason = f"Highest trust wins: {win['system']} ({params.get(TRUST_KEY.get(win['system'], ''), 0.5)})"
        if not win:
            ranked = sorted(cands, key=lambda r: (order.index(r["system"]) if r["system"] in order else len(order), r["loadDate"]))
            win = ranked[0]
            reason = f"{win['system']} wins for {label.lower()}" + (f" (priority {order.index(win['system']) + 1} of {len(order)})" if win["system"] in order else " (only source)")
        winners[attr] = {"xid": win["xid"], "system": win["system"], "reason": reason, "policy": win.get("policy") if win["kind"] == "agent" else pid,
                         "value": win["attrs"][attr]}
        if attr not in EXTENDED:
            rec[attr] = win["attrs"][attr]
    rec["survivors"] = winners
    rec["winners"] = {k: [w["system"], w["policy"]] for k, w in winners.items()}
    return rec


def seed(rec):
    """Builds XREF rows for a seeded record from its older cross-references."""
    if rec.get("xrefs") is not None:
        return rec
    xs = [from_xref(x) for x in rec.get("crossReferences", [])]
    if rec.get("duns"):
        xs.append(row("D&B", rec["duns"], {"legalName": rec.get("legalName"), "duns": rec.get("duns"), "parent": rec.get("parent")}, kind="enrichment", load="2026-11-09"))
    if rec["id"] == "BRR-0004417":
        loads = ["2023-06-02", "2023-06-02", "2024-01-15", "2023-06-02", "2025-02-11"]
        for x, d in zip(xs, loads):
            x["loadDate"] = d
        xs.append(row("Address validation", "AV-0004417", {"address": "1200 E WHITESTONE BLVD, CEDAR PARK TX 78613-3047"}, kind="enrichment", load="2026-11-09"))
    rec["xrefs"] = xs
    return rec


def remove_request_rows(rec, request_id):
    rec["xrefs"] = [x for x in rec.get("xrefs", []) if x["sourceKey"] != request_id]


def table(rec):
    """One row per contributing source, one column per attribute; the winning cell is marked."""
    sv = rec.get("survivors") or {}
    used = [a for a, _ in ATTRS if any(a in x["attrs"] for x in rec.get("xrefs", []))]
    rows = []
    for x in rec.get("xrefs", []):
        rows.append({"xid": x["xid"], "system": x["system"], "sourceKey": x["sourceKey"], "loadDate": x["loadDate"], "kind": x["kind"],
                     "policy": x.get("policy"), "cells": [{"attr": a, "v": x["attrs"].get(a), "win": sv.get(a, {}).get("xid") == x["xid"]} for a in used]})
    return {"attributes": [{"key": a, "label": LABEL[a]} for a in used], "rows": rows,
            "survivors": [{"attribute": LABEL[a], "key": a, **sv[a]} for a in used if a in sv]}


def split(rec, xid):
    """Unmerge: takes one XREF row out of a record; returns the row."""
    keep, out = [], None
    for x in rec.get("xrefs", []):
        if x["xid"] == xid and out is None:
            out = x
        else:
            keep.append(x)
    rec["xrefs"] = keep
    return copy.deepcopy(out)
