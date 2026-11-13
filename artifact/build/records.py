from common import *
from journey import T, KV, CK, TX, P

W = lambda v, pol=None: {"v": v, "win": True, "policy": pol or ""}

cedar = {"id": "BRR-0004417", "name": "Cedar Park Family Pharmacy, LLC", "status": "Active", "sub": "Independent pharmacy · Cedar Park, TX · 5 sources", "sections": [
  KV([("Legal name", "Cedar Park Family Pharmacy, LLC", "From D&B", "SV-001"),
      ("DUNS", "61-203-4471", "Confidence code 10"),
      ("Address", "1200 E Whitestone Blvd, Cedar Park, TX 78613-3047", "Standardized", "SV-001"),
      ("Tax ID", "••-•••5846", "TIN match passed", "SV-001"),
      ("Sales areas", "Pharma · US01 · Specialty · US02", "US02 added Nov 12"),
      ("Cross-references", "5 sources: 3 SAP, 1 Oracle EBS, 1 AS/400", "")], "Key details"),
  T(["System", "System ID", "Name as held there", "Merged"], [
      ["SAP S/4HANA", "0001004417", "CEDAR PARK FAMILY PHARMACY LLC", "2023-06-02"],
      ["SAP S/4HANA", "0001004418", "Cedar Park Family Pharmacy", "2023-06-02"],
      ["SAP S/4HANA", "0001009902", "CEDAR PARK FAMILY PHARM", "2024-01-15"],
      ["Oracle EBS", "ORA-88213", "Cedar Pk Family Pharmacy Inc", "2023-06-02"],
      ["AS/400 Order Entry", "AS4-30771", "CEDAR PARK FAM PHCY", "2025-02-11 · steward confirmed"]], "Cross-references", level=2, meta="5 source records"),
  T(["Attribute", "Business ready record", "Winning source", "Why it won"], [
      ["Legal name", "Cedar Park Family Pharmacy, LLC", "D&B", P("SV-001")],
      ["Address", "1200 E WHITESTONE BLVD, CEDAR PARK TX 78613-3047", "Address validation", P("SV-001")],
      ["Tax ID", "••-•••5846", "SAP 0001004417 (validated W-9)", P("SV-001")],
      ["Payment terms", "Net 30", "SAP 0001004417", P("BR-PT-001")],
      ["Credit limit", "$50,000", "SAP 0001004417", P("BR-CR-001")],
      ["Payment method", "ACH", "Account validation GREEN", P("BR-PM-001")],
      ["DEA", "FC2201846 · II–V", "LexisNexis", P("SV-001")]], "Winning values", level=2),
  T(["Attribute", "Business ready record", "SAP 0001004417", "SAP 0001004418", "SAP 0001009902", "Oracle EBS ORA-88213", "AS/400 AS4-30771"], [
      ["Name", "Cedar Park Family Pharmacy, LLC", "CEDAR PARK FAMILY PHARMACY LLC", "Cedar Park Family Pharmacy", "CEDAR PARK FAMILY PHARM", "Cedar Pk Family Pharmacy Inc", "CEDAR PARK FAM PHCY"],
      ["Street", "1200 E Whitestone Blvd", W("1200 E WHITESTONE BLVD", "SV-001"), "1200 E Whitestone Blvd Ste 4", "1200 E WHITESTONE", "1200 Whitestone Blvd", "1200 E WHITESTONE BLVD STE 4"],
      ["Postal code", "78613-3047", W("78613-3047", "SV-001"), "78613", "78613", "78613", "—"],
      ["Tax ID", "••-•••5846", W("••-•••5846", "SV-001"), "••-•••5846", "••-•••5846", "••-•••5846", "missing"],
      ["Payment terms", "Net 30", W("NT30", "BR-PT-001"), "NT30", "NT45", "N30", "NET 30"],
      ["Credit limit", "$50,000", W("50,000", "BR-CR-001"), "25,000", "0", "—", "—"],
      ["Account group", "Sold-to", "Z001 sold-to", "Z002 ship-to", "Z003 payer", "—", "—"]], "Full comparison", level=3, meta="Highlighted cells won"),
  T(["When", "Change", "By"], [
      ["Nov 12, 2026 2:21 PM", "Sales area Specialty · US02 added (REQ-10495)", "Match & merge agent"],
      ["Nov 9, 2026", "D&B refresh: employees 19 → 22", "Enrichment agent"],
      ["Feb 11, 2025", "AS/400 AS4-30771 merged", "J. Ortiz, data steward"]], "History", level=3),
]}

lakeside = {"id": "BRR-0051207", "name": "Lakeside Community Pharmacy, LLC", "status": "Active", "sub": "Independent pharmacy · Tyler, TX · created Nov 12", "sections": [
  KV([("Legal name", "Lakeside Community Pharmacy, LLC", "D&B, matches W-9", "SV-001"),
      ("DBA", "Lakeside Pharmacy", "Requester confirmed"),
      ("DUNS", "08-447-3921", "Confidence code 9"),
      ("Address", "1420 S Broadway Ave, Ste 200, Tyler, TX 75701-3318", "Standardized", "SV-001"),
      ("Sales area", "Pharma · US01", ""),
      ("Cross-references", "1 source: SAP 0001051207 (created from this record)", "")], "Key details"),
  KV([("Payment terms", "Net 30", "", "BR-PT-001"), ("Credit limit", "$75,000", "Approved by credit manager", "BR-CR-001"),
      ("Payment method", "ACH", "", "BR-PM-001"), ("Pricing group", "Independent retail", "", "BR-PR-001"),
      ("Tax class", "Exempt for resale", "", "BR-TX-001"), ("Controlled ordering", "CII–CV on", "", "RG-CS-001"),
      ("Partners", "Sold-to = bill-to = payer · 1 ship-to", "", "BR-PF-001")], "Extended · Pharma · US01", level=2),
  T(["System", "System ID", "Name as held there", "Linked"], [["SAP S/4HANA", "0001051207", "LAKESIDE COMMUNITY PHARMACY LLC", "Nov 12, 2026"]], "Cross-references", level=2),
  KV([("Parent", "Lakeside Rx Holdings, LLC", "D&B"), ("Related account", "Lakeside Pharmacy #2 · SAP 0000042871", "Same owner, separate customer")], "Family and related accounts", level=3),
]}

DATA = {"records": [cedar, lakeside]}

JS = r'''
    const D = this.data();
    const ri = this.state.r || 0;
    const rec = D.records[ri];
    const depth = this.state.depth || 1;
    const p = this.prep(rec.sections, depth);
    const list = D.records.map((r, i) => ({ id: r.id, name: r.name, sub: r.sub, current: i === ri ? 'true' : 'false',
      style: i === ri ? 'border-color: #1D47B8; background: #F5F8FF' : 'border-color: #E2E6EC; background: #FFFFFF',
      pick: () => this.setState({ r: i, depth: 1 }) }));
    return Object.assign({ list, rid: rec.id, rname: rec.name, rsub: rec.sub, rstatus: rec.status,
      moreLabel: depth === 1 ? 'Show sources and winning values' : 'Show full comparison and history',
      more: () => this.setState({ depth: depth + 1 }), less: () => this.setState({ depth: 1 }) }, p);
'''

BODY = f'''{title_block("Records / Business ready records", "Business ready records", "Each record shows its key details first. Use … to open the source records it was built from, the value that won for each attribute and the policy that decided it.")}
<div style="display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start">
<div role="list" aria-label="Records" style="flex: 1 1 260px; display: flex; flex-direction: column; gap: 8px">
<sc-for list="{{{{list}}}}" as="it" hint-placeholder-count="2">
<button type="button" role="listitem" aria-current="{{{{it.current}}}}" onClick="{{{{it.pick}}}}" style="display: flex; flex-direction: column; align-items: flex-start; gap: 3px; padding: 12px 14px; border-radius: 12px; border: 1px solid; font-family: inherit; text-align: left; cursor: pointer; {{{{it.style}}}}">
<span style="font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 12px; color: #4B5563">{{{{it.id}}}}</span>
<span style="font-size: 14px; font-weight: 600; color: #131820">{{{{it.name}}}}</span>
<span style="font-size: 12px; color: #5F6B7A">{{{{it.sub}}}}</span>
</button>
</sc-for>
</div>
<div style="flex: 999 1 560px; min-width: 0; display: flex; flex-direction: column; gap: 14px">
<div style="display: flex; flex-wrap: wrap; align-items: center; gap: 10px; padding: 18px 20px; {CARD}">
<span style="font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 13px; color: #4B5563">{{{{rid}}}}</span>
<h2 style="margin: 0; font-size: 20px; line-height: 26px; font-weight: 600">{{{{rname}}}}</h2>
<span style="font-size: 12px; font-weight: 600; color: #0E5A32; background: #EEF7F1; border-radius: 999px; padding: 3px 10px">{{{{rstatus}}}}</span>
<span style="flex-basis: 100%; font-size: 13px; color: #5F6B7A">{{{{rsub}}}}</span>
</div>
{SECTIONS}
</div>
</div>'''

write("Records.dc.html", page("Records.dc.html", "Business ready records", BODY, js_class(DATA, JS), 1700))
print("records ok")
