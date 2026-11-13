from common import *
from journey import T, KV, CK, TX, P

H = json.load(open(os.path.join(REPO, "data", "hierarchy", "brazos-health-system.json")))
DNB = {o["organization"]["duns"]: o for o in json.load(open(os.path.join(REPO, "data", "dnb", "organizations.json")))["organizations"]}
nodes = H["nodes"]
kids = {}
for n in nodes:
    kids.setdefault(n["parent"], []).append(n["id"])

out = []
for i, n in enumerate(nodes):
    sap = f"000{2000000 + i * 37:07d}"
    brr = f"BRR-{3000 + i:07d}"
    d = DNB.get((n.get("duns") or "").replace("-", ""), {}).get("organization", {})
    ch = kids.get(n["id"], [])
    secs = [KV([("Type", n["kind"], ""), ("DUNS", n.get("duns") or "—", "D&B" if n.get("duns") else "Ship-to, no DUNS"),
                ("Location", n.get("address") or f"{n['city']}, {n['state']}", ""),
                ("Status", n["status"], "From D&B family tree; not yet in the hub" if n["status"] == "Proposed" else ""),
                ("Children", str(len(ch)), "")], "Key details")]
    if n["level"] >= 2 and n["kind"] != "Ship-to":
        secs.append(KV([("DEA", f"{n['dea']} · II–V", "Active to Mar 31, 2027", "RG-CS-001"),
                        ("State license", n["license"], "Active", "RG-CS-001"),
                        ("NPI", n["npi"], ""),
                        ("Exclusion lists", "OFAC, OIG, SAM clear", "LexisNexis, Nov 9", "AG-002")], "Compliance", level=2))
    secs.append(T(["System", "System ID", "Role"], [["Business ready record", brr, "Hub"], ["SAP S/4HANA", sap, "Sold-to" if n["kind"] != "Ship-to" else "Ship-to"]] +
                  ([["Oracle EBS", f"ORA-{40000 + i}", "Legacy order entry"]] if i % 3 == 0 else []), "Cross-references", level=2))
    if d:
        secs.append(KV([("Employees", str(d["numberOfEmployees"][0]["value"]), "Consolidated"), ("Started", d["startDate"], ""),
                        ("Failure score class", f"{d['dnbAssessment']['failureScore']['classScore']} of 5", ""),
                        ("Global ultimate", d["corporateLinkage"]["globalUltimate"]["primaryName"], "")], "From D&B", level=3))
    if n["level"] in (1, 2):
        secs.append(KV([("Pharma · US01", "Net 45 from the IDN contract · pricing IDN Tier 2", "", "BR-PT-001"),
                        ("Partners", "Bill-to and payer at the regional system", "", "BR-PF-001"),
                        ("Credit", "Shares the parent's $4.5M limit", "", "BR-CR-001")], "Extended attributes", level=3))
    out.append({"id": n["id"], "name": n["name"], "kind": n["kind"], "level": n["level"], "parent": n["parent"],
                "status": n["status"], "kids": len(ch), "brr": brr, "sections": secs})

DATA = {"nodes": out, "summary": H["summary"]}

JS = r'''
    const D = this.data();
    const exp = this.state.exp || { 'N-0001': true, 'N-0002': true };
    const sel = this.state.sel || 'N-0003';
    const depth = this.state.depth || 1;
    const byId = {}; D.nodes.forEach((n) => { byId[n.id] = n; });
    const visibleNode = (n) => { let p = n.parent; while (p) { if (!exp[p]) return false; p = byId[p].parent; } return true; };
    const rows = D.nodes.filter(visibleNode).map((n) => {
      const isSel = n.id === sel;
      const toggle = () => { const e = Object.assign({}, exp); e[n.id] = !e[n.id]; this.setState({ exp: e }); };
      return { id: n.id, name: n.name, kind: n.kind, kids: n.kids, hasKids: n.kids > 0,
        sign: exp[n.id] ? '−' : '+', expanded: exp[n.id] ? 'true' : 'false',
        pad: 'padding-left: ' + (n.level * 22) + 'px',
        style: isSel ? 'background: #EAF0FE; border-color: #9DB3EE; color: #1D47B8' : (n.status === 'Proposed' ? 'background: #FFF1DE; border-color: #F2B872; color: #7A3B00' : 'background: #FFFFFF; border-color: #E2E6EC; color: #131820'),
        badge: n.status === 'Proposed' ? 'Proposed' : '', pressed: isSel ? 'true' : 'false',
        pick: () => this.setState({ sel: n.id, depth: 1 }), toggle };
    });
    const node = byId[sel];
    const p = this.prep(node.sections, depth);
    const expandAll = () => { const e = {}; D.nodes.forEach((n) => { if (n.kids) e[n.id] = true; }); this.setState({ exp: e }); };
    const collapse = () => this.setState({ exp: { 'N-0001': true } });
    return Object.assign({ rows, nName: node.name, nKind: node.kind, nBrr: node.brr, sumLE: D.summary.legalEntities, sumST: D.summary.shipToAccounts, sumN: D.summary.nodes,
      expandAll, collapse, moreLabel: 'Show more', more: () => this.setState({ depth: depth + 1 }), less: () => this.setState({ depth: 1 }) }, p);
'''

BODY = f'''{title_block("Records / Hierarchies", "Brazos Health System", "Corporate family from D&B joined to the hub. Click a node to see its details; double-click to expand or collapse it.")}
<div style="display: flex; flex-wrap: wrap; gap: 10px; font-size: 13px">
<span style="padding: 6px 12px; {CARD}"><strong>{{{{sumLE}}}}</strong> legal entities</span>
<span style="padding: 6px 12px; {CARD}"><strong>{{{{sumST}}}}</strong> ship-to accounts</span>
<span style="padding: 6px 12px; {CARD}"><strong>{{{{sumN}}}}</strong> nodes</span>
<span style="padding: 6px 12px; border-radius: 14px; background: #FFF1DE; border: 1px solid #F2B872; color: #7A3B00">1 proposed from D&amp;B</span>
</div>
<div style="display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start">
<section aria-label="Hierarchy" style="flex: 1 1 420px; min-width: 0; display: flex; flex-direction: column; gap: 10px; padding: 16px; {CARD}">
<div style="display: flex; flex-wrap: wrap; gap: 8px"><button type="button" onClick="{{{{expandAll}}}}" style="{BTN}">Expand all</button><button type="button" onClick="{{{{collapse}}}}" style="{BTN}">Collapse</button></div>
<ul role="tree" style="margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 4px; max-height: 1180px; overflow-y: auto">
<sc-for list="{{{{rows}}}}" as="r" hint-placeholder-count="12">
<li role="treeitem" aria-expanded="{{{{r.expanded}}}}" style="display: flex; align-items: center; gap: 6px; {{{{r.pad}}}}">
<sc-if value="{{{{r.hasKids}}}}" hint-placeholder-val="{{{{true}}}}"><button type="button" onClick="{{{{r.toggle}}}}" aria-label="Expand or collapse" style="flex: 0 0 auto; width: 32px; height: 32px; border-radius: 8px; border: 1px solid #CDD3DC; background: #FFFFFF; font-family: inherit; font-size: 16px; cursor: pointer">{{{{r.sign}}}}</button></sc-if>
<button type="button" aria-pressed="{{{{r.pressed}}}}" onClick="{{{{r.pick}}}}" onDoubleClick="{{{{r.toggle}}}}" style="flex: 1; min-width: 0; display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; min-height: 44px; box-sizing: border-box; padding: 8px 12px; border-radius: 10px; border: 1px solid; font-family: inherit; text-align: left; cursor: pointer; {{{{r.style}}}}">
<span style="font-size: 13px; font-weight: 600">{{{{r.name}}}}</span>
<span style="font-size: 12px; color: #5F6B7A">{{{{r.kind}}}}</span>
<sc-if value="{{{{r.badge}}}}" hint-placeholder-val="{{{{false}}}}"><span style="font-size: 11px; font-weight: 600">{{{{r.badge}}}}</span></sc-if>
</button>
</li>
</sc-for>
</ul>
</section>
<section aria-label="Node detail" style="flex: 1 1 420px; min-width: 0; display: flex; flex-direction: column; gap: 14px">
<div style="display: flex; flex-direction: column; gap: 8px; padding: 18px 20px; {CARD}">
<span style="font-size: 12px; color: #5F6B7A">{{{{nKind}}}}</span>
<h2 style="margin: 0; font-size: 20px; line-height: 26px; font-weight: 600">{{{{nName}}}}</h2>
<a href="Records.dc.html" style="{BTN_DARK}; align-self: flex-start">Open Business ready record {{{{nBrr}}}}</a>
</div>
{SECTIONS}
</section>
</div>'''

write("Hierarchy.dc.html", page("Hierarchy.dc.html", "Hierarchies", BODY, js_class(DATA, JS), 1720))
print("hierarchy ok")
