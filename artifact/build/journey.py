from common import *

def T(cols, rows, title, level=1, meta=""):
    return {"title": title, "kind": "table", "level": level, "meta": meta, "cols": cols, "rows": [{"cells": r} for r in rows]}

def KV(rows, title, level=1, meta=""):
    return {"title": title, "kind": "kv", "level": level, "meta": meta,
            "rows": [dict(k=r[0], v=r[1], note=(r[2] if len(r) > 2 else ""), policy=(r[3] if len(r) > 3 else "")) for r in rows]}

def CK(rows, title, level=1, meta=""):
    return {"title": title, "kind": "checks", "level": level, "meta": meta,
            "rows": [dict(k=r[0], note=r[2], policy=(r[3] if len(r) > 3 else "")) | {"pass": r[1]} for r in rows]}

def TX(text, title, level=1, meta=""):
    return {"title": title, "kind": "text", "level": level, "meta": meta, "text": text}

def P(id_):
    return {"v": "", "policy": id_}

def stage(key, name, actor, status, summary, policies, sections):
    return dict(key=key, name=name, actor=actor, status=status, summary=summary, policies=policies, sections=sections)

# ------------------------------------------------------------------ S3: brand-new customer
s3 = [
 stage("intake", "Intake", "agent", "34 fields · 0.97 avg", "Read an email thread and 4 attachments and turned them into 34 key values mapped to the customer data model.", ["AG-002"], [
   KV([("Channel", "Email to the onboarding inbox", "Thread of 3 messages"),
       ("From", "purchasing@lakesiderx.com", "Dana Whitfield, owner"),
       ("Attachments", "W-9 · TX pharmacy license · DEA certificate · TX resale certificate", "4 documents"),
       ("Request", "Become a customer; order brand and generic Rx, including CII–CV", "")], "What came in"),
   T(["Extracted field", "Value", "Confidence", "Maps to"], [
       ["Legal name", "Lakeside Community Pharmacy, LLC", "0.99", "Customer.LegalName"],
       ["DBA", "Lakeside Pharmacy", {"v": "0.82 · requester confirmed", "policy": "AG-002"}, "Customer.DBA"],
       ["Address", "1420 S Broadway Ave, Ste 200, Tyler, TX 75701", "0.98", "Address.Street / City / Region / Postal"],
       ["Tax ID", "••-•••9212", "0.97", "TaxNumber1 (EIN)"],
       ["DEA registration", "FL4827311 · schedules II–V", "0.99", "Regulatory.DEA"],
       ["State license", "TX-PH-481220", "0.98", "Regulatory.StateLicense"],
       ["Sales area", "Pharma · sales org US01", "0.95", "SalesArea"],
       ["Contact", "Dana Whitfield · (903) 555-0148", "0.96", "Contact.Primary"]], "Key values", meta="8 of 34 shown"),
   T(["Extracted field", "Value", "Confidence", "Maps to"], [
       ["Resale certificate", "TX 01-728-4410, issued 2026-10-02", "0.94", "Tax.ResaleCertificate"],
       ["Bank routing / account", "111000025 / ••••7302", "0.99", "Bank.Routing / Bank.Account"],
       ["Business type", "Independent retail pharmacy", "0.93", "Customer.Type"],
       ["Requested terms", "Net 45", "0.91", "Requested.PaymentTerms"],
       ["Expected monthly volume", "$60,000–$80,000", "0.88", "Requested.Volume"]], "More key values", level=2),
   TX("Dana Whitfield (Nov 11, 4:02 PM): We'd like to open an account for Lakeside Community Pharmacy in Tyler. Documents attached.\nOnboarding (Nov 11, 4:40 PM): Thanks, Dana. Please send your resale certificate as well.\nDana Whitfield (Nov 12, 9:10 AM): Attached. We trade as Lakeside Pharmacy.", "Email thread", level=3),
 ]),
 stage("search", "Search before create", "agent", "5 candidates · best 0.71", "Searched the hub by name, address, tax ID and DEA. No candidate reached 0.80, so no existing customer matches.", ["MM-002"], [
   T(["#", "Record", "System ID", "Confidence", "Why"], [
       ["1", "Lakeside Pharmacy #2, Tyler", "SAP 0000042871", "0.71", "Same owner, different tax ID and address"],
       ["2", "Lakeside Community Pharmacy, Waco", "SAP 0001010027", "0.63", "Same name, different city"],
       ["3", "Lakeside Drug Inc, Tyler", "Oracle EBS LEG-70004", "0.52", "Similar name, different tax ID"],
       ["4", "Lakeside Health Mart, Frisco", "SAP 0001010019", "0.44", "Similar name"],
       ["5", "Lakeview Pharmacy, Tyler", "SAP 0001010033", "0.38", "Same city"]], "Matching records", meta="Threshold 0.80"),
   KV([("Decision", "Create a new customer", "No candidate at or above 0.80", "MM-002"),
       ("Related record", "Lakeside Pharmacy #2 kept as a related account", "Same owner")], "Outcome"),
   KV([("Index searched", "Business ready records and source cross-references", ""),
       ("Blocking keys", "Name tokens · ZIP 757 · tax ID · DEA", ""),
       ("Records compared", "1,284", "after blocking")], "How the search ran", level=2),
 ]),
 stage("match", "Match & merge", "agent", "No merge", "No merge needed. Each attribute of the new record takes its value from the most trusted source.", ["SV-001", "MM-002"], [
   T(["Attribute", "Value", "Winning source", "Policy"], [
       ["Legal name", "Lakeside Community Pharmacy, LLC", "D&B (matches W-9)", P("SV-001")],
       ["Address", "1420 S BROADWAY AVE STE 200, TYLER TX 75701-3318", "Address validation", P("SV-001")],
       ["Tax ID", "••-•••9212", "W-9, TIN match passed", P("SV-001")],
       ["DEA", "FL4827311", "LexisNexis", P("SV-001")]], "Survivorship"),
 ]),
 stage("enrich", "Enrichment", "agent", "+21 fields", "Added 21 fields from D&B, LexisNexis and address validation to the 34 from intake.", ["SV-001", "AG-002"], [
   T(["Source", "Fields", "Examples"], [
       ["Intake", "34", "Legal name, address, tax ID, DEA, bank details"],
       ["D&B", "12", "DUNS, parent, global ultimate, NAICS, employees, failure score"],
       ["LexisNexis", "6", "Business registration, license status, exclusion checks"],
       ["Address validation", "3", "Standardized address, ZIP+4, deliverability"]], "Fields by source", meta="55 fields"),
   KV([("DUNS", "08-447-3921", "Confidence code 9", "AG-002"),
       ("Parent", "Lakeside Rx Holdings, LLC", "D&B family tree"),
       ("Global ultimate", "Lakeside Rx Holdings, LLC", ""),
       ("NAICS", "456110 · Pharmacies and drug retailers", ""),
       ("Started", "2019", "Business registration 2019-05-14"),
       ("Employees", "18", "Single site"),
       ("Failure score class", "3 of 5", "Moderate risk")], "From D&B", level=2),
 ]),
 stage("validate", "Validation", "agent", "7 of 7 calls passed", "Called 7 validation services. All passed; one exclusion-list name hit scored below the review line.", ["RG-CS-001", "AG-002", "BR-PM-001"], [
   T(["Service", "Check", "Result", "Time"], [
       ["Address validation", "USPS CASS standardization", "Deliverable · DPV Y · commercial", "180 ms"],
       ["IRS TIN matching", "EIN and legal name", "Match", "620 ms"],
       ["Account validation", "Routing 111000025 · ••••7302", "GREEN · open · owner name match", "410 ms"],
       ["DEA registration", "FL4827311", "Active to Jun 30, 2027 · II–V", "350 ms"],
       ["Texas State Board of Pharmacy", "TX-PH-481220", "Active to Jun 30, 2027", "290 ms"],
       ["OFAC · OIG LEIE · SAM.gov", "Entity and owner", "Clear", "540 ms"],
       ["Name screening", "\"Lakeside Pharmacy Services\" on OIG", {"v": "0.41 · below 0.80, cleared", "policy": "AG-002"}, "120 ms"]], "API calls"),
   TX("POST /v1/address/standardize → 200 {\"dpv\":\"Y\",\"zip4\":\"3318\",\"rdi\":\"C\"}\nPOST /v2/account/verify → 200 {\"code\":\"GREEN\",\"nameMatch\":\"match\"}\nGET /dea/registrations/FL4827311 → 200 {\"status\":\"ACTIVE\",\"expires\":\"2027-06-30\"}", "Call log", level=2),
 ]),
 stage("legal", "Legal", "agent", "3 of 3 rules", "Standard terms accepted. Licensure and DEA allow controlled-substance ordering.", ["BR-LG-001", "RG-CS-001"], [
   CK([("Standard terms of sale accepted without edits", True, "Signed in the portal Nov 12", "BR-LG-001"),
       ("State pharmacy license active", True, "TX-PH-481220 to Jun 30, 2027", "RG-CS-001"),
       ("DEA active for requested schedules II–V", True, "Controlled ordering on", "RG-CS-001")], "Rules applied", meta="3 of 3 passed"),
 ]),
 stage("procurement", "Procurement", "agent", "2 of 2 rules", "Pricing group and partner functions set from the customer type.", ["BR-PR-001", "BR-PF-001"], [
   CK([("Independent retail pharmacy with no contract", True, "Pricing group: Independent retail", "BR-PR-001"),
       ("Single site, no billing parent", True, "Sold-to = bill-to = payer; 1 ship-to", "BR-PF-001")], "Rules applied", meta="2 of 2 passed"),
 ]),
 stage("credit", "Credit", "human", "Credit manager approved", "Proposed a $75,000 limit, above the agent's $50,000 authority, so a credit manager approved it. Terms Net 30, payment by ACH.", ["BR-CR-001", "BR-PT-001", "BR-PM-001"], [
   CK([("Proposed limit $75,000 from D&B score and expected volume", True, "Failure score class 3", "BR-CR-001"),
       ("Limit within agent authority (up to $50,000)", "human", "Above authority; approved by Marcus Lee, credit manager, 11:02 AM", "BR-CR-001"),
       ("Requested Net 45 needs credit tier A and 12 months trading", False, "Tier B; Net 30 applied", "BR-PT-001"),
       ("Default terms Net 30", True, "Applied", "BR-PT-001"),
       ("Account validation GREEN", True, "Payment method ACH", "BR-PM-001")], "Rules applied", meta="3 passed · 1 not met · 1 approved by a person"),
 ]),
 stage("tax", "Tax", "agent", "1 of 1 rule", "Valid Texas resale certificate for a Texas ship-to, so the customer is exempt for resale.", ["BR-TX-001"], [
   CK([("Resale certificate present, state matches ship-to, not expired", True, "TX 01-728-4410", "BR-TX-001")], "Rules applied", meta="1 of 1 passed"),
 ]),
 stage("record", "Business ready record", "agent", "BRR-0051207 created", "New Business ready record created and sent to S/4HANA and Snowflake.", ["AG-003"], [
   KV([("Record", "BRR-0051207", "Active"), ("Legal name", "Lakeside Community Pharmacy, LLC", "", "SV-001"),
       ("Payment terms", "Net 30", "", "BR-PT-001"), ("Credit limit", "$75,000", "Approved by credit manager", "BR-CR-001"),
       ("Tax class", "Exempt for resale", "", "BR-TX-001"), ("Controlled ordering", "CII–CV on", "", "RG-CS-001")], "Key attributes"),
   KV([("S/4HANA", "Customer 0001051207 · sales org US01", "customer.created sent 11:04 AM"),
       ("Snowflake", "Loaded 11:05 AM", "")], "Sent to", level=2),
 ]),
]

# ------------------------------------------------------------------ S1: request for a customer that already exists
s1 = [
 stage("intake", "Intake", "agent", "12 fields · 0.98 avg", "Read an email thread with 2 attachments. The request is to add a Specialty account for an existing pharmacy.", ["AG-002"], [
   KV([("Channel", "Email to the onboarding inbox", "Thread of 3 messages"), ("From", "ap@cedarparkfamilyrx.com", ""),
       ("Attachments", "W-9 · TX pharmacy license", "2 documents"), ("Request", "Add Specialty account for oncology drugs", "")], "What came in"),
   T(["Extracted field", "Value", "Confidence", "Maps to"], [
       ["Legal name", "Cedar Park Family Pharmacy LLC", "0.99", "Customer.LegalName"],
       ["Address", "1200 E Whitestone Blvd, Cedar Park, TX 78613", "0.98", "Address"],
       ["Tax ID", "••-•••5846", "0.98", "TaxNumber1 (EIN)"],
       ["Request type", "Add sales area", "0.96", "Request.Type"],
       ["Sales area", "Specialty · sales org US02", "0.97", "SalesArea"]], "Key values", meta="5 of 12 shown"),
 ]),
 stage("search", "Search before create", "agent", "Existing customer found · 0.98", "Found the customer already in the hub. The 4 other hits are source records already merged into it.", ["MM-002"], [
   T(["#", "Record", "System ID", "Confidence", "Status"], [
       ["1", "Cedar Park Family Pharmacy, LLC", "BRR-0004417", {"v": "0.98", "win": True}, "Business ready record"],
       ["2", "Cedar Park Family Pharmacy", "SAP 0001004418", "0.96", "Cross-reference of BRR-0004417"],
       ["3", "CEDAR PARK FAMILY PHARM", "SAP 0001009902", "0.93", "Cross-reference of BRR-0004417"],
       ["4", "Cedar Pk Family Pharmacy Inc", "Oracle EBS ORA-88213", "0.91", "Cross-reference of BRR-0004417"],
       ["5", "CEDAR PARK FAM PHCY", "AS/400 AS4-30771", "0.84", "Cross-reference; merge confirmed by a steward in 2025"]], "Matching records", meta="Threshold 0.95 to link"),
   KV([("Decision", "Do not create a customer; link the request to BRR-0004417", "0.98 is above 0.95", "MM-002")], "Outcome"),
 ]),
 stage("match", "Match & merge", "agent", "Linked to BRR-0004417", "The request was linked to the existing record. Only the new Specialty sales area is added.", ["MM-002", "SV-001"], [
   T(["Attribute", "In request", "In record", "Result"], [
       ["Legal name", "Cedar Park Family Pharmacy LLC", "Cedar Park Family Pharmacy, LLC", {"v": "Kept record value", "policy": "SV-001"}],
       ["Address", "1200 E Whitestone Blvd", "1200 E WHITESTONE BLVD, CEDAR PARK TX 78613-3047", {"v": "Kept record value", "policy": "SV-001"}],
       ["Sales area", "Specialty · US02", "Pharma · US01", {"v": "Added US02", "win": True}]], "What changed"),
 ]),
 stage("enrich", "Enrichment", "agent", "D&B refreshed", "D&B refreshed with no change to name, parent or address.", ["SV-001"], [
   KV([("DUNS", "Unchanged", ""), ("Parent", "None (independent)", ""), ("Employees", "22 (was 19)", "Updated")], "D&B refresh"),
 ]),
 stage("validate", "Validation", "agent", "3 of 3 calls passed", "License and DEA re-checked for the new sales area.", ["RG-CS-001"], [
   T(["Service", "Result"], [["Texas State Board of Pharmacy", "Active to Mar 31, 2027"], ["DEA registration", "Active · II–V"], ["OFAC · OIG · SAM", "Clear"]], "API calls"),
 ]),
 stage("legal", "Legal", "agent", "1 of 1 rule", "Standard terms already on file cover the new sales area.", ["BR-LG-001"], [
   CK([("Standard terms on file, no edits", True, "Accepted 2024-03-18", "BR-LG-001")], "Rules applied"),
 ]),
 stage("procurement", "Procurement", "agent", "2 of 2 rules", "Specialty oncology pricing group from the customer's GPO membership.", ["BR-PR-001", "BR-PF-001"], [
   CK([("GPO membership verified", True, "Pricing group: Specialty oncology", "BR-PR-001"),
       ("Partner functions follow the existing account", True, "Sold-to = bill-to = payer", "BR-PF-001")], "Rules applied"),
 ]),
 stage("credit", "Credit", "agent", "Within authority", "The Specialty account shares the existing $50,000 limit. Net 30 and ACH carried over.", ["BR-CR-001", "BR-PT-001", "BR-PM-001"], [
   CK([("Shares existing limit $50,000", True, "Within agent authority", "BR-CR-001"),
       ("Payment terms Net 30", True, "From the record", "BR-PT-001"),
       ("ACH, account validation GREEN", True, "", "BR-PM-001")], "Rules applied", meta="3 of 3 passed"),
 ]),
 stage("tax", "Tax", "agent", "1 of 1 rule", "Resale certificate on file is valid.", ["BR-TX-001"], [
   CK([("Resale certificate valid for TX", True, "Expires 2027-12-31", "BR-TX-001")], "Rules applied"),
 ]),
 stage("record", "Business ready record", "agent", "BRR-0004417 updated", "No new customer. Specialty US02 added to the existing record. Touchless end to end.", ["AG-003"], [
   KV([("Record", "BRR-0004417", "Updated 2:21 PM"), ("Change", "Sales area Specialty · US02 added", ""), ("Cross-references", "5: 3 SAP, 1 Oracle EBS, 1 AS/400", "")], "Key attributes"),
 ]),
]

# ------------------------------------------------------------------ S2: existing site, new owner
s2 = [
 stage("intake", "Intake", "agent", "18 fields · 0.96 avg", "Web form asking to set up a new customer at an address already in the hub.", ["AG-002"], [
   T(["Extracted field", "Value", "Confidence", "Maps to"], [
       ["Legal name", "Westbrook Infusion Partners LP", "0.99", "Customer.LegalName"],
       ["Address", "4500 W Park Blvd Ste 120, Plano, TX 75093", "0.99", "Address"],
       ["Tax ID", "••-•••0896", "0.98", "TaxNumber1 (EIN)"],
       ["Request type", "New customer", "0.99", "Request.Type"]], "Key values", meta="4 of 18 shown"),
 ]),
 stage("search", "Search before create", "agent", "2 candidates · best 0.89", "Found the same site under a different tax ID.", ["MM-002", "MM-007a"], [
   T(["#", "Record", "System ID", "Confidence", "Why"], [
       ["1", "Westbrook Infusion Center LLC", "SAP 0001003388", "0.89", "Same site, different tax ID"],
       ["2", "Westbrook Infusion Ctr", "Oracle EBS ORA-55102", "0.86", "Same site"]], "Matching records"),
 ]),
 stage("match", "Match & merge", "agent", "Successor created", "D&B reports an ownership change, so a new customer is created and linked as successor. No merge.", ["MM-007a"], [
   CK([("Match 0.80 or above, address exact, tax ID differs", True, "0.89", "MM-007a"),
       ("Ownership change within 365 days", True, "D&B: acquired 2026-09-02", "MM-007a"),
       ("Carry over ship-to and delivery instructions", True, "Dock 2, 7 AM–3 PM", "MM-007a"),
       ("Reset credit limit and payment terms", True, "Sent to Credit", "MM-007a")], "Rules applied"),
 ]),
 stage("enrich", "Enrichment", "agent", "+16 fields", "D&B confirms the new owner and its parent.", ["SV-001"], [
   KV([("New owner", "Westbrook Infusion Partners LP", "D&B"), ("Parent", "Northstar Infusion Holdings", "D&B family tree"), ("Ownership change", "Sep 2, 2026", "")], "From D&B"),
 ]),
 stage("validate", "Validation", "human", "Steward confirmed bank", "Account validation returned AMBER: the bank account still shows the prior owner. A steward confirmed with a call-back.", ["BR-PM-001", "AG-002"], [
   T(["Service", "Result"], [["Address validation", "Deliverable"], ["IRS TIN matching", "Match"], ["Account validation", {"v": "AMBER · partial name match", "policy": "BR-PM-001"}], ["OFAC · OIG · SAM", "Clear"]], "API calls"),
   CK([("Bank account holder matches legal name", "human", "Steward call-back to known contact; confirmed new account opening", "BR-PM-001")], "Person needed"),
 ]),
 stage("legal", "Legal", "agent", "1 of 1 rule", "New owner accepted standard terms.", ["BR-LG-001"], [
   CK([("Standard terms accepted without edits", True, "", "BR-LG-001")], "Rules applied"),
 ]),
 stage("procurement", "Procurement", "agent", "2 of 2 rules", "Pricing and partners carried from the site.", ["BR-PR-001", "BR-PF-001"], [
   CK([("IDN contract carried to new owner", True, "Pricing IDN Tier 2", "BR-PR-001"), ("Ship-to carried over", True, "", "BR-PF-001")], "Rules applied"),
 ]),
 stage("credit", "Credit", "human", "Waiting on credit manager", "Limit reset after the ownership change. Proposed $120,000 needs a credit manager.", ["BR-CR-001", "MM-007a", "BR-PT-001"], [
   CK([("Limit reset after ownership change", True, "Prior limit $120,000 not carried", "MM-007a"),
       ("Proposed $120,000 within agent authority", "human", "Above $50,000; assigned to a credit manager", "BR-CR-001"),
       ("Payment terms Net 30 until Credit decides", True, "", "BR-PT-001")], "Rules applied"),
 ]),
 stage("tax", "Tax", "human", "Certificate requested", "Resale certificate is in the prior owner's name, so the customer is taxable until a new one arrives.", ["BR-TX-001"], [
   CK([("Resale certificate in the customer's own name", False, "Certificate names Westbrook Infusion Center LLC", "BR-TX-001")], "Rules applied"),
 ]),
 stage("record", "Business ready record", "agent", "BRR-0051311 pending", "New record linked as successor of BRR-0003388. The old record deactivates in 30 days if it has no open orders.", ["MM-007a", "AG-003"], [
   KV([("Record", "BRR-0051311", "Pending credit"), ("Successor of", "BRR-0003388", "", "MM-007a"), ("Old record", "Deactivates Dec 12, 2026 if no open orders", "", "MM-007a")], "Key attributes"),
 ]),
]

DATA = {"scenarios": [
  {"tab": "New customer", "sub": "Lakeside Community Pharmacy", "id": "REQ-10482", "outcome": "BRR-0051207 created", "touch": "1 person · credit approval", "stages": s3},
  {"tab": "Customer already exists", "sub": "Cedar Park Family Pharmacy", "id": "REQ-10495", "outcome": "Linked to BRR-0004417", "touch": "Touchless", "stages": s1},
  {"tab": "Existing site, new owner", "sub": "Westbrook Infusion Partners", "id": "REQ-10501", "outcome": "Successor BRR-0051311 pending", "touch": "3 people · bank, credit, tax", "stages": s2},
]}

AG = "background: #EAF0FE; border: 1px solid #9DB3EE; color: #1D47B8"
HU = "background: #FFF1DE; border: 1px solid #F2B872; color: #7A3B00"

JS = r'''
    const D = this.data();
    const si = this.state.sc || 0;
    const sc = D.scenarios[si];
    const openKey = this.state.open || sc.stages[0].key;
    const depth = this.state.depth || 1;
    const tabs = D.scenarios.map((s, i) => ({
      label: s.tab, sub: s.sub, current: i === si ? 'true' : 'false',
      style: i === si ? 'border-color: #131820; background: #131820; color: #FFFFFF' : 'border-color: #CDD3DC; background: #FFFFFF; color: #131820',
      pick: () => this.setState({ sc: i, open: null, depth: 1 }),
    }));
    const stages = sc.stages.map((st, i) => {
      const sel = st.key === openKey;
      const base = st.actor === 'human' ? '%HU%' : '%AG%';
      return Object.assign({}, st, {
        n: i + 1, actorLabel: st.actor === 'human' ? 'Person' : 'Agent',
        style: base + (sel ? '; box-shadow: 0 0 0 3px #131820' : ''),
        open: () => this.setState({ open: st.key, depth: 1 }),
        pressed: sel ? 'true' : 'false',
      });
    });
    const st = sc.stages.find((s) => s.key === openKey) || sc.stages[0];
    const p = this.prep(st.sections, depth);
    return Object.assign({
      tabs, stages, scId: sc.id, outcome: sc.outcome, touch: sc.touch,
      dName: st.name.replace('&amp;', '&'), dSummary: st.summary, dActor: st.actor === 'human' ? 'A person was needed' : 'Agent acted on its own',
      dActorStyle: st.actor === 'human' ? '%HU%' : '%AG%',
      dPolicies: st.policies.map((id) => ({ id, tip: this.tip(id) })),
      moreLabel: 'Show more detail (level ' + (depth + 1) + ' of ' + p.maxLevel + ')',
      more: () => this.setState({ depth: depth + 1 }), less: () => this.setState({ depth: 1 }),
    }, p);
'''.replace("%HU%", HU).replace("%AG%", AG)

BODY = f'''<div style="display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 16px">
{title_block("Records / Request journey", "Request journey", "Every request runs through the core MDM agents and then the Legal, Procurement, Credit and Tax agents. Double-click a stage to see what it did. Hover a policy ID to see which policy decided it.")}
<div style="display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; color: #4B5563">
<span style="display: inline-flex; align-items: center; gap: 6px"><span aria-hidden="true" style="width: 12px; height: 12px; border-radius: 3px; {AG}"></span>Agent acted on its own</span>
<span style="display: inline-flex; align-items: center; gap: 6px"><span aria-hidden="true" style="width: 12px; height: 12px; border-radius: 3px; {HU}"></span>A person was needed</span>
</div>
</div>

<div role="tablist" aria-label="Scenario" style="display: flex; flex-wrap: wrap; gap: 8px">
<sc-for list="{{{{tabs}}}}" as="t" hint-placeholder-count="3">
<button type="button" role="tab" aria-selected="{{{{t.current}}}}" onClick="{{{{t.pick}}}}" style="display: flex; flex-direction: column; align-items: flex-start; gap: 2px; min-height: 52px; box-sizing: border-box; padding: 8px 14px; border-radius: 10px; border: 1px solid; font-family: inherit; cursor: pointer; {{{{t.style}}}}"><span style="font-size: 14px; font-weight: 600">{{{{t.label}}}}</span><span style="font-size: 12px; opacity: 0.8">{{{{t.sub}}}}</span></button>
</sc-for>
</div>

<section style="display: flex; flex-direction: column; gap: 16px; padding: 20px; {CARD}">
<div style="display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 20px">
<span style="font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 13px; color: #4B5563">{{{{scId}}}}</span>
<span style="font-size: 15px; font-weight: 600">{{{{outcome}}}}</span>
<span style="font-size: 13px; color: #5F6B7A">{{{{touch}}}}</span>
</div>
<ol aria-label="Stages" style="margin: 0; padding: 0; list-style: none; display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px">
<sc-for list="{{{{stages}}}}" as="s" hint-placeholder-count="10">
<li style="display: flex">
<button type="button" aria-pressed="{{{{s.pressed}}}}" onClick="{{{{s.open}}}}" onDoubleClick="{{{{s.open}}}}" title="Double-click for detail" style="flex: 1; display: flex; flex-direction: column; align-items: flex-start; gap: 4px; min-height: 96px; box-sizing: border-box; padding: 10px 12px; border-radius: 12px; font-family: inherit; text-align: left; cursor: pointer; {{{{s.style}}}}">
<span style="font-size: 11px; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; opacity: 0.85">{{{{s.n}}}} · {{{{s.actorLabel}}}}</span>
<span style="font-size: 14px; font-weight: 600; line-height: 19px">{{{{s.name}}}}</span>
<span style="font-size: 12px; line-height: 17px; color: #2B323C">{{{{s.status}}}}</span>
</button>
</li>
</sc-for>
</ol>
</section>

<section aria-label="Stage detail" style="display: flex; flex-direction: column; gap: 14px">
<div style="display: flex; flex-direction: column; gap: 8px; padding: 18px 20px; {CARD}">
<div style="display: flex; flex-wrap: wrap; align-items: center; gap: 10px">
<h2 style="margin: 0; font-size: 20px; line-height: 26px; font-weight: 600">{{{{dName}}}}</h2>
<span style="font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 999px; {{{{dActorStyle}}}}">{{{{dActor}}}}</span>
</div>
<p style="margin: 0; font-size: 14px; line-height: 21px; color: #2B323C">{{{{dSummary}}}}</p>
<div style="display: flex; flex-wrap: wrap; align-items: center; gap: 6px"><span style="font-size: 12px; color: #5F6B7A">Policies considered</span>
<sc-for list="{{{{dPolicies}}}}" as="pp"><span title="{{{{pp.tip}}}}" tabindex="0" style="{CHIP}">{{{{pp.id}}}}</span></sc-for></div>
</div>
{SECTIONS}
</section>'''

write("Journey.dc.html", page("Journey.dc.html", "Request journey", BODY, js_class(DATA, JS), 1940))
print("journey ok")
