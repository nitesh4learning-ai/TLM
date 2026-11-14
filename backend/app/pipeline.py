"""The agent pipeline: core MDM agents, then the Legal, Procurement, Credit and Tax function agents.

Every decision cites the policy that drove it. Stages a policy reserves for a person are marked actor="human"
and status "waiting" until someone approves them in the steward queue.
"""
import datetime
import re

from . import llm, policystore, providers, rules, store, xref
from .reference import SAP, LEGACY, sim, name_sim, addr_sim, norm, street_of
from .llm import FIELDS

MAP = dict(FIELDS)


def kv(rows, title, level=1, meta=""):
    return {"title": title, "kind": "kv", "level": level, "meta": meta,
            "rows": [{"k": r[0], "v": r[1], "note": r[2] if len(r) > 2 else "", "policy": r[3] if len(r) > 3 else ""} for r in rows]}


def table(cols, rows, title, level=1, meta=""):
    return {"title": title, "kind": "table", "level": level, "meta": meta, "cols": cols,
            "rows": [{"cells": [c if isinstance(c, dict) else {"v": c} for c in r]} for r in rows]}


def checks(rows, title, level=1):
    passed = sum(1 for r in rows if r[1] is True)
    return {"title": title, "kind": "checks", "level": level, "meta": f"{passed} of {len(rows)} passed",
            "rows": [{"k": r[0], "pass": r[1], "note": r[2], "policy": r[3] if len(r) > 3 else ""} for r in rows]}


def stage(key, name, actor, status, summary, policies, sections, waiting_for=None):
    return {"key": key, "name": name, "actor": actor, "status": status, "summary": summary, "policies": policies, "sections": sections,
            "state": "waiting" if actor == "human" else "done", "waitingFor": waiting_for, "explanation": ""}


def v(fields, k):
    f = fields.get(k) or {}
    val = f.get("value") if isinstance(f, dict) else f
    return None if val in ("", None, "null") else str(val)


LABEL = {"legal_name": "Legal name", "address": "Address", "tax_id": "Tax ID (EIN)", "w9_provided": "W-9 form", "dea": "DEA registration",
         "state_license": "State license", "resale_certificate": "Resale certificate"}


def _lite(mail):
    if not mail:
        return None
    return {k: mail.get(k, "") for k in ("subject", "from", "to", "date", "body")} | {
        "attachments": [{"name": a["name"], "bytes": a.get("bytes", 0), "text": a.get("text", "")} for a in mail.get("attachments", [])]}


def mask(tax):
    digits = re.sub(r"\D", "", tax or "")
    return f"••-•••{digits[-4:]}" if len(digits) >= 4 else "—"


# ------------------------------------------------------------------ search corpus
def corpus():
    recs = store.records()
    owner = {}
    for r in recs.values():
        for x in r.get("crossReferences", []):
            owner[(x["system"], x["id"])] = r["id"]
        for x in r.get("xrefs") or []:
            owner[(x["system"], x["sourceKey"])] = r["id"]
    items = []
    for s in SAP:
        items.append({"system": "SAP S/4HANA", "id": s["KUNNR"], "name": s["NAME1"], "address": f"{s['STRAS']}, {s['ORT01']} {s['PSTLZ']}",
                      "tax": s["STCD1"], "brr": owner.get(("SAP S/4HANA", s["KUNNR"]))})
    for l in LEGACY:
        items.append({"system": l["system"], "id": l["legacyId"], "name": l["customerName"], "address": l["addressLine"],
                      "tax": l["taxRef"], "brr": owner.get((l["system"], l["legacyId"]))})
    for r in recs.values():
        items.append({"system": "Business ready record", "id": r["id"], "name": r["legalName"], "address": r["address"], "tax": r.get("taxId"), "brr": r["id"]})
    return items


def score(req, item):
    name = name_sim(req["name"], item["name"])
    addr = addr_sim(req["address"], item["address"])
    rt, it = re.sub(r"\D", "", req.get("tax") or ""), re.sub(r"\D", "", item.get("tax") or "")
    tax = 1.0 if rt and it and rt == it else (0.5 if not rt or not it else 0.0)
    entity = 0.45 * name + 0.35 * addr + 0.20 * tax
    site = 0.6 * addr + 0.4 * name if addr > 0.9 else 0
    s = max(entity, site)
    why = []
    if name > 0.85: why.append("same name")
    elif name > 0.6: why.append("similar name")
    if addr > 0.9: why.append("same site")
    elif addr < 0.5: why.append("different address")
    if tax == 1.0: why.append("same tax ID")
    elif tax == 0.0: why.append("different tax ID")
    return round(min(s, 0.99), 2), ", ".join(why) or "weak match", addr > 0.9, tax == 0.0


# ------------------------------------------------------------------ the run
def run(request_id, fields, intake_summary, mail=None, channel="Email", mode="auto"):
    t_start = datetime.datetime.now()
    P = policystore.Runtime()
    link_at, review_from = P.param("MM-002", "link_at", 0.95), P.param("MM-002", "review_from", 0.80)
    i_auto, i_low = P.param("AG-002", "intake_auto", 0.95), P.param("AG-002", "intake_steward_below", 0.75)
    AUTO_LIMIT = P.param("BR-CR-001", "agent_limit", 50000)
    now = datetime.datetime.now().strftime("%b %d, %Y %I:%M %p")
    legal = v(fields, "legal_name") or "(no legal name)"
    address = v(fields, "address") or ""
    tax = v(fields, "tax_id")
    req_type = v(fields, "request_type") or "New customer"
    sales_area = v(fields, "sales_area") or "Pharma · US01"
    ctype = v(fields, "customer_type") or "Independent retail pharmacy"
    stages = []

    # ---- Intake
    rows, low = [], []
    for f, target in FIELDS:
        val = v(fields, f)
        if val is None:
            continue
        conf = float((fields.get(f) or {}).get("confidence", 0.9) or 0.9)
        shown = mask(val) if f == "tax_id" else val
        cell = {"v": f"{conf:.2f}"}
        if conf < i_auto:
            cell = {"v": f"{conf:.2f} · " + ("requester confirms" if conf >= i_low else "steward review"), "policy": "AG-002"}
            low.append((f, conf))
        rows.append([f.replace("_", " ").capitalize(), shown, cell, target, (fields.get(f) or {}).get("source", "")])
    came = [("Channel", channel, ""), ("Received", now, "")]
    if mail:
        came += [("From", mail.get("from") or "—", ""), ("Subject", mail.get("subject") or "—", ""),
                 ("Attachments", " · ".join(a["name"] for a in mail.get("attachments", [])) or "None", f"{len(mail.get('attachments', []))} documents")]
        if mail.get("to"):
            came.insert(3, ("To", mail["to"], ""))
    very_low = [f for f, c in low if c < i_low]
    sections = [kv(came, "What came in"),
                table(["Extracted field", "Value", "Confidence", "Maps to"], [r[:4] for r in rows[:8]], "Key values", meta=f"{min(8, len(rows))} of {len(rows)} shown"),
                table(["Extracted field", "Value", "Confidence", "Maps to", "Found in"], rows, "All key values", level=2)]
    if mail:
        sections.append({"title": "Email and attachments", "kind": "text", "level": 3, "meta": "",
                         "text": (mail.get("body") or "")[:4000] + "".join(f"\n\n[{a['name']}]\n{(a.get('text') or '')[:800]}" for a in mail.get("attachments", []))})
    stages.append(stage("intake", "Intake", "human" if P.gate("AG-002", very_low) else "agent",
                        f"{len(rows)} fields" + (f" · {len(very_low)} need a steward" if very_low else ""),
                        intake_summary or f"Extracted {len(rows)} key values and mapped them to the customer data model.", ["AG-002"], sections,
                        waiting_for="Data steward" if very_low else None))

    # ---- mandatory fields (DQ-INT-001): block the request until the requester supplies them
    required = [x.strip() for x in str(P.param("DQ-INT-001", "required_fields", "legal_name, address, tax_id, w9_provided")).split(",") if x.strip()]
    def present(f):
        val = v(fields, f)
        return bool(val) and not (f.endswith("_provided") and not val.lower().startswith("y"))
    missing_req = [f for f in required if not present(f)] if P.assigned("Intake", "DQ-INT-001") else []
    if missing_req and P.gate("DQ-INT-001", True):
        it = stages[0]
        it.update(actor="human", state="waiting", waitingFor="Requester", status="Blocked: " + ", ".join(LABEL.get(f, f) for f in missing_req) + " missing",
                  summary=f"The request is blocked because DQ-INT-001 requires {', '.join(LABEL.get(f, f) for f in missing_req)}. "
                          "Edit the request to supply it, or reject it and ask the requester to send it.")
        it["policies"] = ["DQ-INT-001"] + [x for x in it["policies"] if x != "DQ-INT-001"]
        it["sections"].insert(0, checks([(LABEL.get(f, f), present(f), "Provided" if present(f) else "Missing", "DQ-INT-001") for f in required], "Required fields"))
        it["agent"], it["policyVersions"] = "Intake", {pid: P.version(pid) for pid in it["policies"]}
        req = {"id": request_id, "created": now, "legalName": legal, "requestType": req_type, "recordId": None, "decision": "blocked",
               "effects": {}, "channel": channel, "stages": stages, "mode": mode, "revealed": 1, "blocked": missing_req,
               "sources": [], "testData": False, "elapsedMs": round((datetime.datetime.now() - t_start).total_seconds() * 1000),
               "fields": fields, "intakeSummary": intake_summary, "mail": _lite(mail)}
        refresh(req)
        store.save_request(req)
        return req

    # ---- Search before create
    q = {"name": legal, "address": address, "tax": tax}
    hits = []
    for it in corpus():
        s, why, same_site, tax_diff = score(q, it)
        if s >= 0.3:
            hits.append(dict(it, score=s, why=why, same_site=same_site, tax_diff=tax_diff))
    hits.sort(key=lambda h: -h["score"])
    # collapse source records owned by the same Business ready record, keep the strongest first
    top = hits[:5]
    best = top[0] if top else None
    best_brr = best["brr"] if best else None
    result_rows = []
    for i, h in enumerate(top):
        status = "Business ready record" if h["system"] == "Business ready record" else (f"Cross-reference of {h['brr']}" if h["brr"] else "Source record")
        result_rows.append([str(i + 1), h["name"], f"{h['system']} {h['id']}" if h["system"] != "Business ready record" else h["id"],
                            {"v": f"{h['score']:.2f}", "win": i == 0 and h["score"] >= link_at}, h["why"], status])
    bs = best["score"] if best else 0
    stages.append(stage("search", "Search before create", "agent", f"{len(top)} candidates · best {bs:.2f}",
                        "Existing customer found." if bs >= link_at else ("Near match found; match & merge decides." if bs >= review_from else f"No candidate reached {review_from:.2f}, so no existing customer matches."),
                        ["MM-002"], [table(["#", "Record", "System ID", "Confidence", "Why", "Status"], result_rows, "Matching records", meta=f"Link at {link_at:.2f} · review from {review_from:.2f}"),
                                     kv([("Records compared", str(len(hits)), "after blocking"), ("Matched on", "Name, street address, tax ID", "")], "How the search ran", level=2)]))

    # ---- Enrichment lookup (used by match & merge for ownership changes)
    city = (address.split(",")[1].strip() if "," in address else "")
    q = {"name": legal, "address": address, "street": street_of(address), "city": city, "tin": tax, "dea": v(fields, "dea") or "",
         "license": v(fields, "state_license") or ""}
    sources = []
    dnb, m = providers.lookup("dnb", q); sources.append(m)

    # ---- Match & merge
    decision, link_to, successor_of = "new", None, None
    if best and bs >= link_at:
        decision, link_to = "link", best_brr or best["id"]
    elif best and bs >= review_from:
        own = dnb and dnb.get("ownershipChangeDate")
        recent = own and (datetime.date.today() - datetime.date.fromisoformat(own)).days <= P.param("MM-007a", "ownership_window_days", 365)
        if best["same_site"] and best["tax_diff"] and recent:
            decision, successor_of = "successor", best_brr
        else:
            decision = "review"
    if decision == "link":
        stages.append(stage("match", "Match & merge", "agent", f"Linked to {link_to}", f"Request linked to {link_to}; no new customer created.", ["MM-002", "SV-001"],
                            [kv([("Decision", f"Link to {link_to}", f"{bs:.2f} is at or above {link_at:.2f}", "MM-002"),
                                 ("Change", f"Add sales area {sales_area}" if req_type == "Add sales area" else "Refresh existing record", "")], "Outcome")]))
    elif decision == "successor":
        stages.append(stage("match", "Match & merge", "agent", "Successor created", f"Same site, different tax ID and a recent ownership change: new customer linked as successor of {successor_of}.",
                            ["MM-007a"], [checks([(f"Match {review_from:.2f} or above, address exact, tax ID differs", True, f"{bs:.2f}", "MM-007a"),
                                                  (f"Ownership change within {P.param('MM-007a', 'ownership_window_days', 365)} days", True, f"D&B: {dnb['ownershipChangeDate']}", "MM-007a"),
                                                  ("Carry over ship-to and delivery instructions", True, "", "MM-007a"),
                                                  ("Reset credit limit and payment terms", True, "Sent to Credit", "MM-007a")], "Rules applied")]))
    elif decision == "review":
        stages.append(stage("match", "Match & merge", "human" if P.gate("MM-002", True) else "agent", "Steward decides", f"Score {bs:.2f} is in the review band; a data steward compares the candidates.", ["MM-002"],
                            [kv([("Best candidate", f"{best['name']} ({best['system']} {best['id']})", f"{bs:.2f}", "MM-002")], "Person needed")], waiting_for="Data steward"))
    else:
        stages.append(stage("match", "Match & merge", "agent", "No merge", f"No candidate at or above {review_from:.2f}. Each attribute of the new record takes its value from the most trusted source.",
                            ["MM-002", "SV-001"], [table(["Attribute", "Value", "Winning source", "Policy"], [
                                ["Legal name", (dnb or {}).get("primaryName") or legal, "D&B" if dnb else "Intake", {"v": "", "policy": "SV-001"}],
                                ["Address", address, "Intake (validated in the next stages)", {"v": "", "policy": "SV-001"}],
                                ["Tax ID", mask(tax), "Tax document", {"v": "", "policy": "SV-001"}]], "Survivorship")]))

    # ---- Enrichment
    lx, lx_m = providers.lookup("lexisnexis", q); sources.append(lx_m)
    if dnb:
        code = int(dnb.get("confidenceCode") or 0)
        e_actor = "human" if P.gate("AG-002", code < P.param("AG-002", "dnb_accept", 8)) else "agent"
        rows = [("DUNS", dnb.get("duns") or "—", f"Confidence code {code}", "AG-002"), ("Legal name", dnb.get("primaryName") or "—", "D&B"),
                ("Parent", dnb.get("parent") or "None (independent)", "D&B family tree"), ("NAICS", dnb.get("naics") or "—", ""),
                ("Started", str(dnb.get("startDate") or "—"), ""), ("Employees", str(dnb.get("employees") or "—"), ""),
                ("Failure score class", f"{dnb.get('failureScoreClass') or '—'} of 5", "")]
        if dnb.get("ownershipChangeDate"):
            rows.append(("Ownership change", dnb["ownershipChangeDate"], f"Prior owner {dnb.get('priorOwner')}"))
        counts = [["Intake", str(len([f for f, _ in FIELDS if v(fields, f)])), "From the request", "Request"],
                  ["D&B", str(len(rows)), "Firmographics and family tree", m["source"]],
                  ["LexisNexis", "4" if lx else "0", "Registration and exclusion screening", lx_m["source"]]]
        stages.append(stage("enrich", "Enrichment", e_actor, f"D&B match · code {code}", f"Added D&B firmographics{' and LexisNexis screening' if lx else ''}.",
                            ["SV-001", "AG-002"], [table(["Source", "Fields", "What", "From"], counts, "Fields by source"), kv(rows, "From D&B", level=2, meta=m["source"])],
                            waiting_for=None if e_actor == "agent" else "Data steward"))
    else:
        stages.append(stage("enrich", "Enrichment", "human", "No D&B match", "D&B returned no match above confidence code 5; a steward identifies the company.", ["AG-002"],
                            [kv([("D&B", "No match" + (f" ({m['error']})" if m["error"] else ""), m["source"], "AG-002")], "Person needed")], waiting_for="Data steward"))

    # ---- Validation
    addr, addr_m = providers.lookup("address", q); sources.append(addr_m)
    tin, tin_m = providers.lookup("irs_tin", q); sources.append(tin_m)
    acct, acct_m = providers.lookup("avs_account", q); sources.append(acct_m)
    dea, dea_m = providers.lookup("dea", q); sources.append(dea_m)
    lic, lic_m = providers.lookup("state_board", q); sources.append(lic_m)
    dea, lic = dea or {}, lic or {}
    wants_cs = (v(fields, "controlled_substances") or "yes").lower().startswith("y")
    calls, issues = [], []

    def row(service, check, result, meta, ok, policy=""):
        cell = {"v": result, "policy": policy} if policy else {"v": result}
        calls.append([service, check, cell, meta["source"] + (f" · error: {meta['error']}" if meta.get("error") else ""), f"{meta['ms']} ms"])
        if not ok:
            issues.append(service.lower())

    # address: Claude standardizes, the address service confirms deliverability
    llm_addr = None
    if llm.available() and address:
        t0 = datetime.datetime.now()
        try:
            llm_addr = llm.standardize_address(address)
        except Exception as e:  # noqa: BLE001
            llm_addr = {"error": str(e)[:150]}
        ms = round((datetime.datetime.now() - t0).total_seconds() * 1000)
        if llm_addr.get("error"):
            calls.append(["Address standardization", address, {"v": "Not available"}, "Claude", f"{ms} ms"])
        else:
            flags = ", ".join(llm_addr.get("issues") or []) or "No issues"
            calls.append(["Address standardization", address, {"v": f"{llm_addr.get('standardized')} · {flags}"}, f"Claude ({llm.MODEL})", f"{ms} ms"])
            if llm_addr.get("poBox") and wants_cs:
                issues.append("PO box ship-to for controlled substances")
    if addr:
        row("Address deliverability", street_of(address) or "—", f"{'Deliverable' if addr.get('deliverable') else 'Not deliverable'} · DPV {addr.get('dpv')} · {addr.get('standardized')}",
            addr_m, bool(addr.get("deliverable")))
        if llm_addr and not llm_addr.get("error") and addr.get("standardized") and addr_sim(llm_addr.get("standardized", ""), addr["standardized"]) < 0.85:
            issues.append("address (Claude and the address service disagree)")
    else:
        row("Address deliverability", street_of(address) or "—", "No result", addr_m, False)
    tres = (tin or {}).get("result", "no result")
    row("IRS TIN matching", mask(tax), {"match": "EIN and legal name match", "name mismatch": f"EIN on file for {tin.get('nameOnFile') if tin else ''}",
                                        "not found": "No record for this EIN", "no tin": "No tax ID in the request"}.get(tres, tres), tin_m, tres == "match")
    if acct:
        row("Account validation", f"{acct.get('routing', '')} · ••••{acct.get('last4', '')}", f"{acct.get('code')} · name {acct.get('nameMatch')}", acct_m,
            acct.get("code") == "GREEN", "BR-PM-001")
    else:
        calls.append(["Account validation", "—", {"v": "No bank account found"}, acct_m["source"], f"{acct_m['ms']} ms"])
    if wants_cs:
        row("DEA registration", dea.get("number") or v(fields, "dea") or "—", f"{dea.get('status') or 'Not found'} to {dea.get('expires') or '—'}", dea_m, dea.get("status") == "Active", "RG-CS-001")
    row("State Board of Pharmacy", lic.get("number") or v(fields, "state_license") or "—", f"{lic.get('status') or 'Not found'}", lic_m, lic.get("status") == "Active", "RG-CS-001")
    if lx:
        clear = all((lx.get(k) or "") == "clear" for k in ("ofac", "oig", "sam"))
        row("OFAC · OIG LEIE · SAM.gov", "Entity and owner", "Clear" if clear else "Possible hit", lx_m, clear, "AG-002")
    else:
        row("OFAC · OIG LEIE · SAM.gov", legal, "No screening result", lx_m, False, "AG-002")
    if acct and acct.get("code") != "GREEN":
        pass  # counted above
    passed = sum(1 for c in calls if c[0] != "Address standardization") - len([i for i in issues if not i.startswith("address (") and not i.startswith("PO box")])
    total = sum(1 for c in calls if c[0] != "Address standardization")
    stages.append(stage("validate", "Validation", "human" if P.gate("AG-002", issues) else "agent", f"{passed} of {total} checks passed",
                        "All validation checks passed." if not issues else "Needs a person: " + ", ".join(issues) + ".",
                        ["RG-CS-001", "AG-002", "BR-PM-001"], [table(["Service", "Check", "Result", "Source", "Time"], calls, "Validation calls",
                                                                      meta="Times are measured")],
                        waiting_for="Data steward" if issues else None))

    # ---- shared context for the rules engine: every business-rule policy tests these attributes
    recs = store.records()
    existing = recs.get(link_to) if link_to else None
    vol = v(fields, "expected_monthly_volume")
    try:
        volume = float(re.sub(r"[^\d.]", "", vol.split("-")[-1].split("–")[-1])) if vol else 0
    except ValueError:
        volume = 0
    fsc = (dnb or {}).get("failureScoreClass", 5)
    tier = "A" if fsc <= 2 else ("B" if fsc == 3 else "C")
    if existing:
        limit = (existing.get("salesAreas") or [{}])[0].get("creditLimit", 0) or 0
    else:
        limit = round(max(volume, 25000) / 5000) * 5000
        if decision == "successor":
            limit = (recs.get(successor_of) or {}).get("salesAreas", [{}])[0].get("creditLimit", 0) or limit
    try:
        years = datetime.date.today().year - int(str((dnb or {}).get("startDate") or "")[:4])
    except ValueError:
        years = None
    cert, holder = v(fields, "resale_certificate"), v(fields, "resale_certificate_name")
    req_terms = v(fields, "requested_terms")
    edited = (v(fields, "edited_terms") or "no").lower().startswith("y")
    ctx = {"record_type": "Customer", "customer_type": ctype, "decision": decision, "credit_tier": tier, "failure_class": fsc,
           "proposed_limit": limit, "years_trading": years, "requested_terms": req_terms,
           "account_validation": (acct or {}).get("code") or "none", "gpo": v(fields, "gpo"), "has_contract": False,
           "has_parent_billing": bool((dnb or {}).get("parent")) and (v(fields, "parent_billing") or "").lower().startswith("y"),
           "certificate_present": bool(cert), "existing_certificate": bool(existing and not cert),
           "certificate_holder_match": (not holder) or name_sim(holder, legal) >= P.param("BR-TX-001", "certificate_name_match", 0.9),
           "edited_terms": edited, "license_status": lic.get("status") or "Not found", "dea_status": dea.get("status") or "Not found", "wants_controlled": wants_cs}

    # the record the agents are changing: the existing record's sales area (link), the predecessor (successor) or nothing (new)
    if existing:
        base = next((sa for sa in existing.get("salesAreas", []) if sa.get("area") == sales_area), {})
    elif decision == "successor":
        base = ((recs.get(successor_of) or {}).get("salesAreas") or [{}])[0]
    else:
        base = {}
    changes = []
    OUT = {"terms": ("Payment terms", "paymentTerms"), "payment_method": ("Payment method", "paymentMethod"), "tax_class": ("Tax class", "taxClass"),
           "pricing_group": ("Pricing group", "pricingGroup"), "partners": ("Partner functions", "partners"), "ordering": ("Controlled ordering", "controlled"),
           "terms_of_sale": ("Terms of sale", "termsOfSale")}

    def change(stage_key, label, key, new, pid):
        old = base.get(key)
        changes.append({"stage": stage_key, "key": key, "raw": new, "attribute": label, "old": "—" if old in (None, "") else (f"${old:,.0f}" if key == "creditLimit" else str(old)),
                        "new": f"${new:,.0f}" if key == "creditLimit" else str(new), "policy": pid, "changed": str(old) != str(new)})

    def changes_section(stage_key):
        rows = [[c["attribute"], c["old"], {"v": c["new"], "win": c["changed"]}, {"v": "", "policy": c["policy"]}] for c in changes if c["stage"] == stage_key]
        return table(["Attribute", "Old value", "New value", "Authorised by"], rows, "Changes to the Business ready record",
                     meta=f"Sales area {sales_area}") if rows else None

    def apply(pid, label, stage_key=None):
        """Runs one policy through the rules engine; returns (check row, outcome, needs a person, who)."""
        pol = P.pols.get(pid)
        r = rules.evaluate(pol, ctx) if pol else {"matched": False, "outcome": {}, "decidedBy": "Data steward", "condition": "Policy not active", "note": ""}
        person = r["decidedBy"] != "Agent"
        needs = P.gate(pid, person)
        shown = ", ".join(f"{k.replace('_', ' ')}: {val}" for k, val in r["outcome"].items()) or "No rule matched; a person decides (AG-001)"
        if stage_key:
            for k, val in r["outcome"].items():
                if k in OUT:
                    change(stage_key, OUT[k][0], OUT[k][1], val, pid)
        note = f"Rule: {r['condition']}" + (f" · {r['note']}" if r.get("note") else "") + (f" · decided by {r['decidedBy']}" if person else "")
        return (f"{label} → {shown}", "human" if needs else True, note, pid), r["outcome"], needs, r["decidedBy"]

    # ---- Legal
    row1, lg, lg_h, lg_who = apply("BR-LG-001", "Terms of sale", "legal")
    row2, cs, cs_h, cs_who = apply("RG-CS-001", "Licensure and controlled substances", "legal")
    rows = [row1, row2]
    legal_human = lg_h or cs_h
    stages.append(stage("legal", "Legal", "human" if legal_human else "agent", f"{sum(r[1] is True for r in rows)} of {len(rows)} rules",
                        "Agreements and licensure checked by the rules engine.", ["BR-LG-001", "RG-CS-001"], [x for x in [changes_section("legal")] if x] + [checks(rows, "Rules applied")],
                        waiting_for=(lg_who if lg_h else cs_who) if legal_human else None))

    # ---- Procurement
    row1, pr, pr_h, pr_who = apply("BR-PR-001", "Pricing group", "procurement")
    row2, pf, pf_h, pf_who = apply("BR-PF-001", "Partner functions", "procurement")
    pricing = pr.get("pricing_group") or "Not set"
    proc_human = pr_h or pf_h
    stages.append(stage("procurement", "Procurement", "human" if proc_human else "agent", f"{sum(r[1] is True for r in (row1, row2))} of 2 rules",
                        f"Pricing group {pricing}; partner functions set.", ["BR-PR-001", "BR-PF-001"], [x for x in [changes_section("procurement")] if x] + [checks([row1, row2], "Rules applied")],
                        waiting_for=(pr_who if pr_h else pf_who) if proc_human else None))

    # ---- Credit
    rows = []
    if decision == "successor":
        rows.append(("Limit reset after ownership change", True, "Prior limit not carried", "MM-007a"))
    change("credit", "Credit limit", "creditLimit", limit, "BR-CR-001")
    row_l, cl, cl_h, cl_who = apply("BR-CR-001", f"Credit limit ${limit:,.0f}" + (" (shared with the existing account)" if existing else ""))
    row_t, pt, pt_h, pt_who = apply("BR-PT-001", "Payment terms", "credit")
    row_m, pm, pm_h, pm_who = apply("BR-PM-001", "Payment method", "credit")
    terms = pt.get("terms") or P.param("BR-PT-001", "default_terms", "Net 30")
    method = pm.get("payment_method") or "Check"
    rows += [row_l, row_t]
    if req_terms and str(req_terms).replace(" ", "").lower() != str(terms).replace(" ", "").lower():
        rows.append((f"Requested {req_terms}", False, f"Credit tier {tier}; {terms} applied", "BR-PT-001"))
    rows.append(row_m)
    credit_human = cl_h or pt_h or pm_h
    who = cl_who if cl_h else pt_who if pt_h else pm_who
    stages.append(stage("credit", "Credit", "human" if credit_human else "agent", f"{who} needed" if credit_human else "Within authority",
                        f"Limit ${limit:,.0f}, {terms}, {method}.", ["BR-CR-001", "BR-PT-001", "BR-PM-001"], [x for x in [changes_section("credit")] if x] + [checks(rows, "Rules applied")],
                        waiting_for=who if credit_human else None))

    # ---- Tax
    row_x, tx, tax_human, tx_who = apply("BR-TX-001", "Tax class", "tax")
    tax_class = tx.get("tax_class") or "Taxable"
    stages.append(stage("tax", "Tax", "human" if tax_human else "agent", tax_class, f"Tax class: {tax_class}." + (f" Certificate names {holder}." if holder and not ctx["certificate_holder_match"] else ""),
                        ["BR-TX-001"], [x for x in [changes_section("tax")] if x] + [checks([row_x], "Rules applied")], waiting_for=tx_who if tax_human else None))

    # ---- Business ready record
    effects = {}
    if existing:
        rid = existing["id"]
        rec = existing
        effects = {"updatedRecord": rid}
        if req_type == "Add sales area" and not any(sa["area"] == sales_area for sa in rec.get("salesAreas", [])):
            effects["addedSalesArea"] = sales_area
            rec.setdefault("salesAreas", []).append({"addedBy": request_id, "area": sales_area, "paymentTerms": terms, "creditLimit": limit, "paymentMethod": method,
                                                     "pricingGroup": pricing, "taxClass": tax_class, "controlled": "CII–CV on" if dea.get("status") == "Active" else "Off"})
        rec.setdefault("history", []).insert(0, {"when": now, "change": f"{req_type}: {sales_area} ({request_id})", "by": "Match & merge agent"})
        summary = f"No new customer. {rid} updated."
    else:
        rid = store.next_id("BRR", recs.keys(), 51206)
        rec = {"id": rid, "status": "Pending", "legalName": (dnb or {}).get("primaryName") or legal, "dba": v(fields, "dba"), "duns": (dnb or {}).get("duns"),
               "address": (addr or {}).get("standardized") or (llm_addr or {}).get("standardized") or address, "taxId": tax, "type": ctype, "parent": (dnb or {}).get("parent"),
               "salesAreas": [{"area": sales_area, "paymentTerms": terms, "creditLimit": limit, "paymentMethod": method, "pricingGroup": pricing,
                               "taxClass": tax_class, "controlled": "CII–CV on" if wants_cs and dea.get("status") == "Active" else "Off"}],
               "winners": {"legalName": ["D&B" if dnb else "Intake", "SV-001"], "address": ["Address validation" if addr else "Intake", "SV-001"],
                           "taxId": ["Tax document", "SV-001"], "paymentTerms": ["Policy", "BR-PT-001"], "creditLimit": ["Credit agent", "BR-CR-001"]},
               "crossReferences": [{"system": "Intake", "id": request_id, "name": legal, "address": address, "taxId": tax, "paymentTerms": req_terms,
                                    "creditLimit": None, "accountGroup": None, "salesOrg": None}],
               "successorOf": successor_of, "requestId": request_id,
               "history": [{"when": now, "change": f"Created from {request_id}", "by": "Orchestrator"}]}
        effects = {"createdRecord": rid}
        summary = f"New Business ready record {rid}" + (f", successor of {successor_of}" if successor_of else "") + "."
    # ---- XREF: the request, the enrichment sources and every agent write become source rows; survivorship picks the values
    rec = xref.seed(rec)
    rec["xrefs"].append(xref.row("Intake", request_id, {"legalName": legal, "dba": v(fields, "dba"), "address": address, "taxId": tax,
                                                       "paymentTerms": req_terms}, kind="intake"))
    if not existing:
        if dnb:
            rec["xrefs"].append(xref.row("D&B", dnb.get("duns") or request_id, {"legalName": dnb.get("primaryName"), "duns": dnb.get("duns"), "parent": dnb.get("parent")},
                                         kind="enrichment") | {"sourceKey": request_id, "xid": f"D&B:{dnb.get('duns')}:{request_id}"})
        if addr and addr.get("standardized"):
            rec["xrefs"].append(xref.row("Address validation", request_id, {"address": addr["standardized"]}, kind="enrichment"))
    AGENT_OF = {"legal": "Legal agent", "procurement": "Procurement agent", "credit": "Credit agent", "tax": "Tax agent"}
    for c in [c for c in changes if c["key"] in xref.LABEL]:
        rec["xrefs"].append(xref.row(AGENT_OF.get(c["stage"], "Agent"), request_id, {c["key"]: c["raw"]}, kind="agent", policy=c["policy"], by=AGENT_OF.get(c["stage"]))
                            | {"xid": f"{AGENT_OF.get(c['stage'])}:{request_id}:{c['key']}"})
    xref.survive(rec, P.pols.get("SV-001"))
    if changes:
        rec.setdefault("history", []).insert(0, {"when": now, "change": f"Extended attributes for {sales_area} set by agents: " +
                                                 "; ".join(f"{c['attribute']} {c['old']} → {c['new']} ({c['policy']})" for c in changes if c["changed"]) + f" ({request_id})",
                                                 "by": "MDM operations agents"})
    if mode != "step":
        store.save_record(rec)
    stages.append(stage("record", "Business ready record", "agent", rid, summary, ["AG-003"] + (["MM-007a"] if successor_of else []),
                        [kv([("Record", rid, rec["status"]), ("Legal name", rec["legalName"], "", "SV-001"), ("Payment terms", terms, "", "BR-PT-001"),
                             ("Credit limit", f"${limit:,.0f}", "", "BR-CR-001"), ("Tax class", tax_class, "", "BR-TX-001")], "Key attributes"),
                         table(["Attribute", "Old value", "New value", "Authorised by"],
                               [[c["attribute"], c["old"], {"v": c["new"], "win": c["changed"]}, {"v": "", "policy": c["policy"]}] for c in changes],
                               "All changes the agents made", meta=f"{sum(c['changed'] for c in changes)} changed")]))

    # ---- policy enforcement: every agent may use only policies assigned to it (or to all agents)
    STAGE_AGENT = {"intake": "Intake", "search": "Search before create", "match": "Match & merge", "enrich": "Enrichment", "validate": "Validation",
                   "legal": "Legal", "procurement": "Procurement", "credit": "Credit", "tax": "Tax", "record": "Orchestrator"}
    for s_ in stages:
        agent = STAGE_AGENT[s_["key"]]
        s_["agent"] = agent
        s_["policyVersions"] = {pid: P.version(pid) for pid in s_["policies"]}
        missing = [pid for pid in s_["policies"] if not P.assigned(agent, pid)]
        if missing:
            s_["actor"], s_["state"] = "human", "waiting"
            s_["waitingFor"] = s_.get("waitingFor") or "Data steward"
            s_["status"] = "No policy assigned"
            s_["summary"] = (f"{', '.join(missing)} {'is' if len(missing) == 1 else 'are'} not assigned to the {agent} agent, so it has no rule to decide by. "
                             "The request goes to a person (AG-001). ") + s_["summary"]
            s_["sections"].insert(0, kv([(pid, (P.pols.get(pid) or {}).get("title", "Not active"), "Not assigned to " + agent, "AG-001") for pid in missing], "No policy assigned"))
        h = [pid for pid in s_["policies"] if P.assigned(agent, pid) and P.level(pid) == "H"]
        if h and s_["actor"] != "human":
            s_["actor"], s_["state"] = "human", "waiting"
            s_["waitingFor"] = (P.roles(h[0]) or ["Data steward"])[0]
            s_["status"] = "A person decides"
            s_["summary"] = f"{h[0]} is set to autonomy H, so a person decides. " + s_["summary"]
        if s_["actor"] == "human" and s_["state"] == "waiting" and not s_.get("waitingFor"):
            s_["waitingFor"] = "Data steward"

    # ---- explanations from Claude (optional)
    if llm.available():
        try:
            ex = llm.explain(stages)
            for s in stages:
                s["explanation"] = ex.get(s["key"], "")
        except Exception as e:  # explanations are a nice-to-have; decisions do not depend on them
            for s in stages:
                s["explanation"] = ""
            stages[0]["llmError"] = str(e)[:200]

    uniq = {}
    for m_ in sources:
        uniq[m_["provider"]] = {k: m_[k] for k in ("provider", "source", "mode")}
    req = {"id": request_id, "created": now, "legalName": legal, "requestType": req_type, "recordId": rid, "decision": decision,
           "effects": effects, "channel": channel, "stages": stages, "mode": mode, "revealed": len(stages),
           "sources": list(uniq.values()), "testData": any(m_["mode"] == "test" for m_ in sources),
           "elapsedMs": round((datetime.datetime.now() - t_start).total_seconds() * 1000),
           "fields": fields, "intakeSummary": intake_summary, "mail": _lite(mail), "changes": changes}
    if mode == "step":
        req.update({"revealed": 1, "pendingRecord": rec, "pendingEffects": effects, "effects": {}})
    refresh(req)
    store.save_request(req)
    return req


def touch(req):
    """Share of the work done by people: stages a person handled, out of the stages that have run."""
    shown = req["stages"][: req.get("revealed", len(req["stages"]))]
    human = sum(1 for s in shown if s["actor"] == "human")
    req["humanTouch"] = round(100 * human / len(shown)) if shown else 0
    req["agentShare"] = 100 - req["humanTouch"]
    req["humanStages"] = human
    req["stagesRun"] = len(shown)


def refresh(req):
    touch(req)
    if req.get("rejected"):
        req["status"] = "Rejected · " + ("email to requester recorded" if req["rejected"].get("action") == "email" else "closed")
        req["touchless"] = False
        return
    if req.get("blocked"):
        req["status"] = "Blocked at intake: " + ", ".join(LABEL.get(f, f) for f in req["blocked"]) + " missing"
        req["touchless"] = False
        return
    shown = req["stages"][: req.get("revealed", len(req["stages"]))]
    waiting = [s for s in shown if s["state"] == "waiting"]
    done = len(shown) == len(req["stages"])
    if waiting:
        req["status"] = "Waiting on " + ", ".join(sorted({s["waitingFor"] for s in waiting}))
    elif not done:
        req["status"] = f"Agent by agent · next: {req['stages'][len(shown)]['name']}"
    else:
        req["status"] = "Complete"
    req["touchless"] = not any(s["actor"] == "human" for s in req["stages"])
    if not waiting and done:
        recs = store.records()
        rec = recs.get(req["recordId"])
        if rec and rec["status"] == "Pending":
            rec["status"] = "Active"
            store.save_record(rec)


def approve(req, key, who, note):
    for s in req["stages"]:
        if s["key"] == key and s["state"] == "waiting":
            s["state"] = "approved"
            s["status"] = f"Approved by {who}"
            s["sections"].append(kv([("Approved by", who, datetime.datetime.now().strftime("%b %d, %I:%M %p")), ("Note", note or "—", "")], "Decision by a person"))
    refresh(req)
    store.save_request(req)
    return req


def undo(req):
    """Undoes what a request did to the Business ready records (keeps the request)."""
    eff = req.get("effects") or {}
    recs = store.records()
    if eff.get("createdRecord") in recs:
        del recs[eff["createdRecord"]]
    rid = eff.get("updatedRecord")
    if rid in recs:
        rec = recs[rid]
        rec["salesAreas"] = [sa for sa in rec.get("salesAreas", []) if sa.get("addedBy") != req["id"]]
        rec["history"] = [h for h in rec.get("history", []) if f"({req['id']})" not in h.get("change", "")]
        xref.remove_request_rows(rec, req["id"])
        xref.survive(rec, policystore.all_policies().get("SV-001"))
    store.write("records", recs)
    req["effects"] = {}


def rerun(req, changed_fields=None, by="Data steward", note="", action="Edited and resubmitted"):
    """Applies corrected key values and runs every agent again on the same request."""
    undo(req)
    fields = dict(req.get("fields") or {})
    changed = []
    for k, val in (changed_fields or {}).items():
        old = (fields.get(k) or {}).get("value") if isinstance(fields.get(k), dict) else fields.get(k)
        if str(old or "") != str(val or ""):
            fields[k] = {"value": val, "confidence": 1.0, "source": f"Edited by {by}"}
            changed.append(f"{LABEL.get(k, k.replace('_', ' '))}: {old or '—'} → {val or '—'}")
    history = list(req.get("history") or [])
    history.append({"when": datetime.datetime.now().strftime("%b %d, %Y %I:%M %p"), "by": by, "action": action,
                    "note": note, "changes": changed})
    new = run(req["id"], fields, req.get("intakeSummary", ""), mail=req.get("mail"), channel=req.get("channel", "Email"), mode=req.get("mode", "auto"))
    for k in ("uploadId", "llm"):
        if k in req:
            new[k] = req[k]
    new["history"] = history
    store.save_request(new)
    return new


def reject(req, reason, action, missing, message, by="Data steward"):
    """Closes the request. action = 'restart' runs it again from intake; 'email' asks the requester to redo intake."""
    if action == "restart":
        return rerun(req, {}, by=by, note=reason, action="Rejected and restarted")
    undo(req)
    for s_ in req["stages"]:
        if s_["state"] == "waiting":
            s_["state"] = "rejected"
            s_["status"] = "Rejected"
    req["rejected"] = {"reason": reason, "action": action, "missing": missing, "by": by,
                       "at": datetime.datetime.now().strftime("%b %d, %Y %I:%M %p"), "email": message}
    req.setdefault("history", []).append({"when": req["rejected"]["at"], "by": by, "action": "Rejected" + (" · email to requester" if action == "email" else ""),
                                          "note": reason, "changes": [f"Missing: {', '.join(missing)}"] if missing else []})
    refresh(req)
    store.save_request(req)
    return req


def delete(req):
    """Removes a request and undoes what it did to the Business ready records."""
    eff = req.get("effects") or {}
    recs = store.records()
    if eff.get("createdRecord") in recs:
        del recs[eff["createdRecord"]]
    rid = eff.get("updatedRecord")
    if rid in recs:
        rec = recs[rid]
        rec["salesAreas"] = [sa for sa in rec.get("salesAreas", []) if sa.get("addedBy") != req["id"]]
        rec["history"] = [h for h in rec.get("history", []) if f"({req['id']})" not in h.get("change", "")]
        xref.remove_request_rows(rec, req["id"])
        xref.survive(rec, policystore.all_policies().get("SV-001"))
    store.write("records", recs)
    reqs = store.requests()
    reqs.pop(req["id"], None)
    store.write("requests", reqs)


class StepBlocked(Exception):
    pass


def advance(req):
    """Agent-by-agent mode: runs (reveals) the next agent. Blocks while a stage waits for a person."""
    n = req.get("revealed", len(req["stages"]))
    if n >= len(req["stages"]):
        raise StepBlocked("All agents have already run.")
    last = req["stages"][n - 1]
    if last["state"] == "waiting":
        raise StepBlocked(f"{last['name']} is waiting for {last['waitingFor']}. Approve it first.")
    req["revealed"] = n + 1
    if req["revealed"] == len(req["stages"]) and req.get("pendingRecord"):
        store.save_record(req.pop("pendingRecord"))
        req["effects"] = req.pop("pendingEffects", {})
    refresh(req)
    store.save_request(req)
    return req
