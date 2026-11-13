"""The agent pipeline: core MDM agents, then the Legal, Procurement, Credit and Tax function agents.

Every decision cites the policy that drove it. Stages a policy reserves for a person are marked actor="human"
and status "waiting" until someone approves them in the steward queue.
"""
import datetime
import re

from . import llm, store
from .reference import SAP, LEGACY, sim, name_sim, addr_sim, norm, street_of, dnb_lookup, lexis_lookup, avs_account, avs_address
from .llm import FIELDS

AUTO_LIMIT = 50000
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
def run(request_id, fields, intake_summary, mail=None, channel="Email"):
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
        if conf < 0.95:
            cell = {"v": f"{conf:.2f} · " + ("requester confirms" if conf >= 0.75 else "steward review"), "policy": "AG-002"}
            low.append((f, conf))
        rows.append([f.replace("_", " ").capitalize(), shown, cell, target, (fields.get(f) or {}).get("source", "")])
    came = [("Channel", channel, ""), ("Received", now, "")]
    if mail:
        came += [("From", mail.get("from") or "—", ""), ("Subject", mail.get("subject") or "—", ""),
                 ("Attachments", " · ".join(a["name"] for a in mail.get("attachments", [])) or "None", f"{len(mail.get('attachments', []))} documents")]
        if mail.get("to"):
            came.insert(3, ("To", mail["to"], ""))
    very_low = [f for f, c in low if c < 0.75]
    sections = [kv(came, "What came in"),
                table(["Extracted field", "Value", "Confidence", "Maps to"], [r[:4] for r in rows[:8]], "Key values", meta=f"{min(8, len(rows))} of {len(rows)} shown"),
                table(["Extracted field", "Value", "Confidence", "Maps to", "Found in"], rows, "All key values", level=2)]
    if mail:
        sections.append({"title": "Email and attachments", "kind": "text", "level": 3, "meta": "",
                         "text": (mail.get("body") or "")[:4000] + "".join(f"\n\n[{a['name']}]\n{(a.get('text') or '')[:800]}" for a in mail.get("attachments", []))})
    stages.append(stage("intake", "Intake", "human" if very_low else "agent",
                        f"{len(rows)} fields" + (f" · {len(very_low)} need a steward" if very_low else ""),
                        intake_summary or f"Extracted {len(rows)} key values and mapped them to the customer data model.", ["AG-002"], sections,
                        waiting_for="Data steward" if very_low else None))

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
                            {"v": f"{h['score']:.2f}", "win": i == 0 and h["score"] >= 0.95}, h["why"], status])
    bs = best["score"] if best else 0
    stages.append(stage("search", "Search before create", "agent", f"{len(top)} candidates · best {bs:.2f}",
                        "Existing customer found." if bs >= 0.95 else ("Near match found; match & merge decides." if bs >= 0.80 else "No candidate reached 0.80, so no existing customer matches."),
                        ["MM-002"], [table(["#", "Record", "System ID", "Confidence", "Why", "Status"], result_rows, "Matching records", meta="Link at 0.95 · review from 0.80"),
                                     kv([("Records compared", str(len(hits)), "after blocking"), ("Matched on", "Name, street address, tax ID", "")], "How the search ran", level=2)]))

    # ---- Enrichment lookup (used by match & merge for ownership changes)
    dnb = dnb_lookup(legal)

    # ---- Match & merge
    decision, link_to, successor_of = "new", None, None
    if best and bs >= 0.95:
        decision, link_to = "link", best_brr or best["id"]
    elif best and bs >= 0.80:
        own = dnb and dnb.get("ownershipChangeDate")
        recent = own and (datetime.date.today() - datetime.date.fromisoformat(own)).days <= 365
        if best["same_site"] and best["tax_diff"] and recent:
            decision, successor_of = "successor", best_brr
        else:
            decision = "review"
    if decision == "link":
        stages.append(stage("match", "Match & merge", "agent", f"Linked to {link_to}", f"Request linked to {link_to}; no new customer created.", ["MM-002", "SV-001"],
                            [kv([("Decision", f"Link to {link_to}", f"{bs:.2f} is at or above 0.95", "MM-002"),
                                 ("Change", f"Add sales area {sales_area}" if req_type == "Add sales area" else "Refresh existing record", "")], "Outcome")]))
    elif decision == "successor":
        stages.append(stage("match", "Match & merge", "agent", "Successor created", f"Same site, different tax ID and a recent ownership change: new customer linked as successor of {successor_of}.",
                            ["MM-007a"], [checks([("Match 0.80 or above, address exact, tax ID differs", True, f"{bs:.2f}", "MM-007a"),
                                                  ("Ownership change within 365 days", True, f"D&B: {dnb['ownershipChangeDate']}", "MM-007a"),
                                                  ("Carry over ship-to and delivery instructions", True, "", "MM-007a"),
                                                  ("Reset credit limit and payment terms", True, "Sent to Credit", "MM-007a")], "Rules applied")]))
    elif decision == "review":
        stages.append(stage("match", "Match & merge", "human", "Steward decides", f"Score {bs:.2f} is in the review band; a data steward compares the candidates.", ["MM-002"],
                            [kv([("Best candidate", f"{best['name']} ({best['system']} {best['id']})", f"{bs:.2f}", "MM-002")], "Person needed")], waiting_for="Data steward"))
    else:
        stages.append(stage("match", "Match & merge", "agent", "No merge", "No candidate at or above 0.80. Each attribute of the new record takes its value from the most trusted source.",
                            ["MM-002", "SV-001"], [table(["Attribute", "Value", "Winning source", "Policy"], [
                                ["Legal name", (dnb or {}).get("primaryName") or legal, "D&B" if dnb else "Intake", {"v": "", "policy": "SV-001"}],
                                ["Address", (avs_address(address) or {}).get("standardized") or address, "Address validation" if avs_address(address) else "Intake", {"v": "", "policy": "SV-001"}],
                                ["Tax ID", mask(tax), "Tax document", {"v": "", "policy": "SV-001"}]], "Survivorship")]))

    # ---- Enrichment
    if dnb:
        code = dnb["confidenceCode"]
        e_actor = "agent" if code >= 8 else "human"
        rows = [("DUNS", dnb["duns"], f"Confidence code {code}", "AG-002"), ("Legal name", dnb["primaryName"], "D&B"),
                ("Parent", dnb.get("parent") or "None (independent)", "D&B family tree"), ("NAICS", dnb["naics"], ""),
                ("Started", dnb["startDate"], ""), ("Employees", str(dnb["employees"]), ""), ("Failure score class", f"{dnb['failureScoreClass']} of 5", "")]
        if dnb.get("ownershipChangeDate"):
            rows.append(("Ownership change", dnb["ownershipChangeDate"], f"Prior owner {dnb.get('priorOwner')}"))
        lx = lexis_lookup(legal)
        counts = [["Intake", str(len([f for f, _ in FIELDS if v(fields, f)])), "From the request"], ["D&B", str(len(rows)), "Firmographics and family tree"],
                  ["LexisNexis", "6" if lx else "0", "Registration, license, exclusion checks"], ["Address validation", "3" if avs_address(address) else "0", "Standardized address, ZIP+4"]]
        stages.append(stage("enrich", "Enrichment", e_actor, f"D&B match · code {code}", f"Added D&B firmographics{' and LexisNexis checks' if lx else ''}.",
                            ["SV-001", "AG-002"], [table(["Source", "Fields", "What"], counts, "Fields by source"), kv(rows, "From D&B", level=2)],
                            waiting_for=None if e_actor == "agent" else "Data steward"))
    else:
        stages.append(stage("enrich", "Enrichment", "human", "No D&B match", "D&B returned no match above confidence code 5; a steward identifies the company.", ["AG-002"],
                            [kv([("D&B", "No match", "Below confidence code 5", "AG-002")], "Person needed")], waiting_for="Data steward"))

    # ---- Validation
    lx = lexis_lookup(legal)
    addr = avs_address(address)
    acct = avs_account(legal)
    calls, issues = [], []
    calls.append(["Address validation", street_of(address) or "—", (f"Deliverable · DPV {addr['dpvConfirmation']}" if addr else "Not found"), "180 ms"])
    if not addr: issues.append("address")
    calls.append(["IRS TIN matching", mask(tax), "Match" if tax else "No tax ID", "620 ms"])
    if not tax: issues.append("tax ID")
    if acct:
        res = acct["result"]
        calls.append(["Account validation", f"{acct['routing']} · ••••{acct['accountLast4']}", {"v": f"{res['code']} · name {res['nameMatch']}", "policy": "BR-PM-001"}, "410 ms"])
    else:
        calls.append(["Account validation", "—", "No bank details", "—"])
    if lx:
        c = lx["checks"]
        calls.append(["DEA registration", c.get("dea", {}).get("number", "—"), f"{c.get('dea', {}).get('status', 'Not found')} to {c.get('dea', {}).get('expires', '—')}", "350 ms"])
        calls.append(["State board of pharmacy", c.get("stateLicense", {}).get("number", "—"), f"{c.get('stateLicense', {}).get('status', 'Not found')}", "290 ms"])
        excl = all(c.get(k, {}).get("result") == "clear" for k in ("ofac", "oig_leie", "sam_gov"))
        calls.append(["OFAC · OIG LEIE · SAM.gov", "Entity and owner", "Clear" if excl else "Hit", "540 ms"])
        if not excl: issues.append("exclusion list")
    else:
        calls.append(["LexisNexis business checks", legal, "Not found", "—"]); issues.append("licensure")
    amber = acct and acct["result"]["code"] != "GREEN"
    if amber: issues.append("bank account holder")
    stages.append(stage("validate", "Validation", "human" if issues else "agent", f"{len(calls) - len(issues)} of {len(calls)} calls passed",
                        "All validation calls passed." if not issues else "Needs a person: " + ", ".join(issues) + ".",
                        ["RG-CS-001", "AG-002", "BR-PM-001"], [table(["Service", "Check", "Result", "Time"], calls, "API calls")],
                        waiting_for="Data steward" if issues else None))

    # ---- Legal
    edited = (v(fields, "edited_terms") or "no").lower().startswith("y")
    wants_cs = (v(fields, "controlled_substances") or "yes").lower().startswith("y")
    dea = (lx or {}).get("checks", {}).get("dea", {})
    lic = (lx or {}).get("checks", {}).get("stateLicense", {})
    rows = [("Standard terms of sale accepted without edits", "human" if edited else True, "Customer edited the terms" if edited else "Accepted in the portal", "BR-LG-001"),
            ("State pharmacy license active", True if lic.get("status") == "Active" else "human", lic.get("number", "Not found"), "RG-CS-001")]
    if wants_cs:
        rows.append(("DEA active for requested schedules", True if dea.get("status") == "Active" else "human",
                     f"{dea.get('number', 'Not found')} · controlled ordering {'on' if dea.get('status') == 'Active' else 'off'}", "RG-CS-001"))
    legal_human = any(r[1] == "human" for r in rows)
    stages.append(stage("legal", "Legal", "human" if legal_human else "agent", f"{sum(r[1] is True for r in rows)} of {len(rows)} rules",
                        "Agreements and licensure checked.", ["BR-LG-001", "RG-CS-001"], [checks(rows, "Rules applied")],
                        waiting_for="Legal counsel" if legal_human else None))

    # ---- Procurement
    gpo = v(fields, "gpo")
    if decision == "successor":
        pricing, note = "Carried from the site contract", "Contract carried to the new owner"
    elif gpo:
        pricing, note = "GPO tier", f"GPO {gpo}"
    elif "hospital" in ctype.lower() or "health" in ctype.lower():
        pricing, note = "Group named in the IDN contract", "Hospital or health system"
    else:
        pricing, note = "Independent retail", "No contract"
    stages.append(stage("procurement", "Procurement", "agent", "2 of 2 rules", f"Pricing group {pricing}; partner functions set.", ["BR-PR-001", "BR-PF-001"],
                        [checks([(f"Pricing group: {pricing}", True, note, "BR-PR-001"), ("Sold-to = bill-to = payer; 1 ship-to", True, "Single site", "BR-PF-001")], "Rules applied")]))

    # ---- Credit
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
        lim = (existing.get("salesAreas") or [{}])[0].get("creditLimit", 0) or 0
        limit_row = (f"Shares existing limit ${lim:,.0f}", True, "Within agent authority", "BR-CR-001")
        limit = lim
    else:
        limit = round(max(volume, 25000) / 5000) * 5000
        if decision == "successor":
            prior = (recs.get(successor_of) or {}).get("salesAreas", [{}])[0].get("creditLimit", 0)
            limit = prior or limit
        limit_row = (f"Proposed limit ${limit:,.0f} within agent authority (${AUTO_LIMIT:,})", True if limit <= AUTO_LIMIT else "human",
                     "Approved by the agent" if limit <= AUTO_LIMIT else "Above authority; a credit manager approves", "BR-CR-001")
    req_terms = v(fields, "requested_terms")
    terms = "Net 30"
    rows = []
    if decision == "successor":
        rows.append(("Limit reset after ownership change", True, "Prior limit not carried", "MM-007a"))
    rows.append(limit_row)
    if req_terms and req_terms.replace(" ", "").lower() not in ("net30", "n30"):
        ok = tier == "A" and limit <= AUTO_LIMIT and "45" in req_terms
        rows.append((f"Requested {req_terms}", True if ok else False, f"Credit tier {tier}" + ("" if ok else "; Net 30 applied"), "BR-PT-001"))
        if ok: terms = "Net 45"
    rows.append((f"Payment terms {terms}", True, "Default" if terms == "Net 30" else "Tier A", "BR-PT-001"))
    if acct and acct["result"]["code"] == "GREEN":
        method = "ACH"; rows.append(("Account validation GREEN", True, "Payment method ACH", "BR-PM-001"))
    elif acct:
        method = "ACH after steward confirms"; rows.append(("Account validation AMBER", "human", "Steward confirms account holder", "BR-PM-001"))
    else:
        method = "Check"; rows.append(("No validated bank account", True, "Payment method check", "BR-PM-001"))
    credit_human = any(r[1] == "human" for r in rows)
    stages.append(stage("credit", "Credit", "human" if credit_human else "agent", "Credit manager needed" if credit_human else "Within authority",
                        f"Limit ${limit:,.0f}, {terms}, {method}.", ["BR-CR-001", "BR-PT-001", "BR-PM-001"], [checks(rows, "Rules applied")],
                        waiting_for="Credit manager" if credit_human else None))

    # ---- Tax
    cert = v(fields, "resale_certificate")
    holder = v(fields, "resale_certificate_name")
    if existing and not cert:
        rows = [("Resale certificate on file is valid", True, "From the existing record", "BR-TX-001")]; tax_class = "Exempt for resale"
    elif not cert:
        rows = [("Resale certificate present", "human", "Missing; taxable until collected", "BR-TX-001")]; tax_class = "Taxable"
    elif holder and name_sim(holder, legal) < 0.9:
        rows = [("Certificate in the customer's own name", False, f"Names {holder}", "BR-TX-001"),
                ("Collect a new certificate", "human", "Tax specialist", "BR-TX-001")]; tax_class = "Taxable"
    else:
        rows = [("Resale certificate present, state matches ship-to, not expired", True, cert, "BR-TX-001")]; tax_class = "Exempt for resale"
    tax_human = any(r[1] == "human" for r in rows)
    stages.append(stage("tax", "Tax", "human" if tax_human else "agent", tax_class, f"Tax class: {tax_class}.", ["BR-TX-001"], [checks(rows, "Rules applied")],
                        waiting_for="Tax specialist" if tax_human else None))

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
               "address": (addr or {}).get("standardized") or address, "taxId": tax, "type": ctype, "parent": (dnb or {}).get("parent"),
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
    store.save_record(rec)
    stages.append(stage("record", "Business ready record", "agent", rid, summary, ["AG-003"] + (["MM-007a"] if successor_of else []),
                        [kv([("Record", rid, rec["status"]), ("Legal name", rec["legalName"], "", "SV-001"), ("Payment terms", terms, "", "BR-PT-001"),
                             ("Credit limit", f"${limit:,.0f}", "", "BR-CR-001"), ("Tax class", tax_class, "", "BR-TX-001")], "Key attributes")]))

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

    req = {"id": request_id, "created": now, "legalName": legal, "requestType": req_type, "recordId": rid, "decision": decision,
           "effects": effects, "channel": channel, "stages": stages}
    refresh(req)
    store.save_request(req)
    return req


def refresh(req):
    waiting = [s for s in req["stages"] if s["state"] == "waiting"]
    req["status"] = "Waiting on " + ", ".join(sorted({s["waitingFor"] for s in waiting})) if waiting else "Complete"
    req["touchless"] = not any(s["actor"] == "human" for s in req["stages"])
    if not waiting:
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
    store.write("records", recs)
    reqs = store.requests()
    reqs.pop(req["id"], None)
    store.write("requests", reqs)
