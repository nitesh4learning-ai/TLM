from common import *

FOLDERS = [("match-survivorship", "Match & survivorship"), ("business-rules", "Business rules · extended attributes"),
           ("regulatory", "Regulatory"), ("bpo-playbooks", "BPO playbooks"), ("agent-policies", "Agent policies")]
FN = dict(FOLDERS)
LV_STYLE = {"A": "background: #EAF0FE; color: #1D47B8; border: 1px solid #9DB3EE",
            "B": "background: #F1ECFB; color: #5B2DA8; border: 1px solid #C9B6EE",
            "H": "background: #FFF1DE; color: #7A3B00; border: 1px solid #F2B872"}


def compiled(p):
    lines = [f"id: {p['id']}", f"stage: {p['stage'].lower().replace(' & ', '_').replace(' ', '_')}", f"agent: {p['agent'].lower()}", f"autonomy: {p['level']}", "rules:"]
    for a, b, c in p["rows"]:
        lines += [f"  - when: \"{a}\"", f"    then: \"{b}\"", f"    decided_by: {'agent' if c == 'Agent' else 'person:' + c.lower().replace(' ', '_')}"]
    lines += ["  - when: no_rule_matches", "    then: route_to_person", "audit: cite_policy_on_every_decision"]
    return "\n".join(lines)


pols = []
for p in POL["policies"]:
    pols.append({"id": p["id"], "title": p["title"], "folder": p["folder"], "folderName": FN[p["folder"]], "agent": p["agent"],
                 "owner": p["owner"], "level": p["level"], "levelName": LEVELS[p["level"]], "levelStyle": LV_STYLE[p["level"]],
                 "stage": p["stage"], "text": p["text"], "exceptions": p["exceptions"],
                 "rows": [{"a": a, "b": b, "c": c, "who": "background: #EAF0FE; color: #1D47B8" if c == "Agent" else "background: #FFF1DE; color: #7A3B00"} for a, b, c in p["rows"]],
                 "related": [{"id": r, "tip": ""} for r in p["cites"]], "yaml": compiled(p), "source": p.get("source", "")})

PJS = r'''
    const D = this.data();
    const folder = this.state.folder || 'all';
    const q = (this.state.q || '').toLowerCase();
    const edits = this.state.edits || {};
    const list = D.policies.filter((p) => (folder === 'all' || p.folder === folder) && (!q || (p.id + ' ' + p.title + ' ' + p.text + ' ' + p.agent).toLowerCase().indexOf(q) >= 0));
    const selId = this.state.sel && list.find((p) => p.id === this.state.sel) ? this.state.sel : (list[0] ? list[0].id : null);
    const sel = D.policies.find((p) => p.id === selId);
    const folders = [{ key: 'all', name: 'All policies' }].concat(D.folders).map((f) => {
      const n = f.key === 'all' ? D.policies.length : D.policies.filter((p) => p.folder === f.key).length;
      return { name: f.name, n, current: folder === f.key ? 'true' : 'false',
        style: folder === f.key ? 'background: #EAF0FE; color: #1D47B8; font-weight: 600' : 'background: transparent; color: #2B323C; font-weight: 500',
        pick: () => this.setState({ folder: f.key, sel: null, editing: false }) };
    });
    const items = list.map((p) => ({ id: p.id, title: p.title, agent: p.agent, level: p.level, levelStyle: p.levelStyle,
      current: p.id === selId ? 'true' : 'false',
      style: p.id === selId ? 'border-color: #1D47B8; background: #F5F8FF' : 'border-color: #E2E6EC; background: #FFFFFF',
      pick: () => this.setState({ sel: p.id, editing: false }) }));
    const matrix = D.policies.map((p) => ({ id: p.id, title: p.title, agent: p.agent, tip: this.tip(p.id),
      a: p.level === 'A' ? '●' : '', b: p.level === 'B' ? '●' : '', h: p.level === 'H' ? '●' : '' }));
    const s = sel || {};
    return {
      folders, items, matrix, none: list.length === 0, q: this.state.q || '',
      onSearch: (e) => this.setState({ q: e.target.value }),
      uploaded: this.state.uploaded || '', hasUpload: !!this.state.uploaded,
      onUpload: (e) => { const f = e.target.files && e.target.files[0]; if (f) this.setState({ uploaded: f.name }); },
      has: !!sel, sId: s.id, sTitle: s.title, sFolder: s.folderName, sAgent: s.agent, sOwner: s.owner, sStage: s.stage,
      sLevel: s.level, sLevelName: s.levelName, sLevelStyle: s.levelStyle, sText: (sel && edits[sel.id]) || s.text,
      sEdited: !!(sel && edits[sel.id]), sExceptions: s.exceptions, sRows: s.rows || [], sYaml: s.yaml, sSource: s.source, hasSource: !!s.source,
      sRelated: (s.related || []).map((r) => ({ id: r.id, tip: this.tip(r.id) })), hasRelated: (s.related || []).length > 0,
      editing: !!this.state.editing, notEditing: !this.state.editing,
      startEdit: () => this.setState({ editing: true, draft: (sel && edits[sel.id]) || s.text }),
      onDraft: (e) => this.setState({ draft: e.target.value }), draft: this.state.draft || '',
      saveEdit: () => { const ed = Object.assign({}, edits); ed[sel.id] = this.state.draft; this.setState({ edits: ed, editing: false }); },
      cancelEdit: () => this.setState({ editing: false }),
    };
'''

PBODY = f'''<div style="display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 16px">
{title_block("Platform / Policy studio", "Policy studio", "The store of every policy the agents run. Each policy has one autonomy level: the agent decides, the agent decides and a person approves above a limit, or a person decides. When no policy applies, the request goes to a person.")}
<div style="display: flex; flex-wrap: wrap; gap: 8px">
<label style="{BTN}; position: relative">Upload policy document<input type="file" accept=".pdf,.docx,.md,.txt" onChange="{{{{onUpload}}}}" style="position: absolute; width: 1px; height: 1px; opacity: 0"></label>
<button type="button" style="{BTN_DARK}">New policy</button>
</div>
</div>
<sc-if value="{{{{hasUpload}}}}" hint-placeholder-val="{{{{false}}}}"><div role="status" style="padding: 12px 16px; border-radius: 12px; background: #EAF0FE; border: 1px solid #9DB3EE; color: #1D47B8; font-size: 13px">Uploaded {{{{uploaded}}}}. The policy agent is drafting rules from it; the draft will appear in its folder for review before anything is published.</div></sc-if>

<div style="display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start">
<nav aria-label="Policy folders" style="flex: 1 1 220px; display: flex; flex-direction: column; gap: 4px; padding: 12px; {CARD}">
<label for="pol-search" style="font-size: 12px; color: #5F6B7A; padding: 0 4px">Search policies</label>
<input id="pol-search" type="search" value="{{{{q}}}}" onChange="{{{{onSearch}}}}" placeholder="ID, title, agent or text" style="height: 44px; box-sizing: border-box; padding: 0 12px; border: 1px solid #CDD3DC; border-radius: 9px; font-family: inherit; font-size: 14px; margin-bottom: 8px">
<sc-for list="{{{{folders}}}}" as="f" hint-placeholder-count="6">
<button type="button" aria-current="{{{{f.current}}}}" onClick="{{{{f.pick}}}}" style="display: flex; align-items: center; justify-content: space-between; gap: 8px; min-height: 44px; padding: 0 12px; border: 0; border-radius: 9px; font-family: inherit; font-size: 13px; text-align: left; cursor: pointer; {{{{f.style}}}}"><span>{{{{f.name}}}}</span><span style="font-size: 12px; color: #5F6B7A">{{{{f.n}}}}</span></button>
</sc-for>
</nav>

<div role="list" aria-label="Policies" style="flex: 1 1 260px; display: flex; flex-direction: column; gap: 8px">
<sc-if value="{{{{none}}}}" hint-placeholder-val="{{{{false}}}}"><p style="margin: 0; padding: 14px; font-size: 13px; color: #5F6B7A; {CARD}">No policy matches. A request with no matching policy goes to a person (AG-001).</p></sc-if>
<sc-for list="{{{{items}}}}" as="it" hint-placeholder-count="6">
<button type="button" role="listitem" aria-current="{{{{it.current}}}}" onClick="{{{{it.pick}}}}" style="display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 12px 14px; border-radius: 12px; border: 1px solid; font-family: inherit; text-align: left; cursor: pointer; {{{{it.style}}}}">
<span style="display: flex; align-items: center; gap: 8px"><span style="font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 12px; color: #4B5563">{{{{it.id}}}}</span><span style="font-size: 11px; font-weight: 700; padding: 1px 7px; border-radius: 6px; {{{{it.levelStyle}}}}">{{{{it.level}}}}</span></span>
<span style="font-size: 14px; font-weight: 600; color: #131820">{{{{it.title}}}}</span>
<span style="font-size: 12px; color: #5F6B7A">Agent: {{{{it.agent}}}}</span>
</button>
</sc-for>
</div>

<sc-if value="{{{{has}}}}" hint-placeholder-val="{{{{true}}}}">
<article style="flex: 999 1 520px; min-width: 0; display: flex; flex-direction: column; gap: 14px; padding: 20px; {CARD}">
<div style="display: flex; flex-wrap: wrap; align-items: center; gap: 10px">
<span style="font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 13px; color: #4B5563">{{{{sId}}}}</span>
<h2 style="margin: 0; font-size: 20px; line-height: 26px; font-weight: 600">{{{{sTitle}}}}</h2>
<span style="font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 999px; {{{{sLevelStyle}}}}">{{{{sLevel}}}} · {{{{sLevelName}}}}</span>
</div>
<div style="display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 13px; color: #4B5563"><span>Folder: {{{{sFolder}}}}</span><span>Stage: {{{{sStage}}}}</span><span>Agent: {{{{sAgent}}}}</span><span>Owner: {{{{sOwner}}}}</span><span>Published v1.0</span></div>
<section style="display: flex; flex-direction: column; gap: 8px">
<div style="display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px"><h3 style="margin: 0; font-size: 14px; font-weight: 600">In plain English</h3>
<sc-if value="{{{{notEditing}}}}" hint-placeholder-val="{{{{true}}}}"><button type="button" onClick="{{{{startEdit}}}}" style="{BTN}">Edit policy</button></sc-if></div>
<sc-if value="{{{{notEditing}}}}" hint-placeholder-val="{{{{true}}}}"><p style="margin: 0; font-size: 14px; line-height: 22px; color: #2B323C">{{{{sText}}}}</p>
<sc-if value="{{{{sEdited}}}}" hint-placeholder-val="{{{{false}}}}"><p style="margin: 0; font-size: 12px; color: #5B2DA8">Draft v1.1 saved. Needs a second governance reviewer before it is published.</p></sc-if></sc-if>
<sc-if value="{{{{editing}}}}" hint-placeholder-val="{{{{false}}}}">
<label for="pol-edit" style="font-size: 12px; color: #5F6B7A">Policy text</label>
<textarea id="pol-edit" value="{{{{draft}}}}" onChange="{{{{onDraft}}}}" rows="5" style="width: 100%; box-sizing: border-box; padding: 10px 12px; border: 1px solid #CDD3DC; border-radius: 9px; font-family: inherit; font-size: 14px; line-height: 21px"></textarea>
<div style="display: flex; flex-wrap: wrap; gap: 8px"><button type="button" onClick="{{{{saveEdit}}}}" style="{BTN_DARK}">Save draft</button><button type="button" onClick="{{{{cancelEdit}}}}" style="{BTN}">Cancel</button></div>
</sc-if>
</section>
<section style="display: flex; flex-direction: column; gap: 8px">
<h3 style="margin: 0; font-size: 14px; font-weight: 600">Conditions and actions</h3>
<div style="overflow-x: auto"><table style="width: 100%; border-collapse: collapse; font-size: 13px; line-height: 19px">
<thead><tr><th scope="col" style="text-align: left; padding: 8px 10px; border-bottom: 1px solid #E2E6EC; font-size: 12px; color: #5F6B7A">Condition</th><th scope="col" style="text-align: left; padding: 8px 10px; border-bottom: 1px solid #E2E6EC; font-size: 12px; color: #5F6B7A">Action</th><th scope="col" style="text-align: left; padding: 8px 10px; border-bottom: 1px solid #E2E6EC; font-size: 12px; color: #5F6B7A">Decided by</th></tr></thead>
<tbody><sc-for list="{{{{sRows}}}}" as="r" hint-placeholder-count="3"><tr><td style="padding: 8px 10px; border-bottom: 1px solid #F1F3F6; vertical-align: top">{{{{r.a}}}}</td><td style="padding: 8px 10px; border-bottom: 1px solid #F1F3F6; vertical-align: top">{{{{r.b}}}}</td><td style="padding: 8px 10px; border-bottom: 1px solid #F1F3F6; vertical-align: top"><span style="display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 12px; font-weight: 600; {{{{r.who}}}}">{{{{r.c}}}}</span></td></tr></sc-for></tbody>
</table></div>
</section>
<p style="margin: 0; font-size: 13px; line-height: 20px; color: #2B323C"><strong>Exceptions.</strong> {{{{sExceptions}}}}</p>
<sc-if value="{{{{hasRelated}}}}" hint-placeholder-val="{{{{false}}}}"><div style="display: flex; flex-wrap: wrap; align-items: center; gap: 6px"><span style="font-size: 12px; color: #5F6B7A">Related policies</span><sc-for list="{{{{sRelated}}}}" as="rr"><span title="{{{{rr.tip}}}}" tabindex="0" style="{CHIP}">{{{{rr.id}}}}</span></sc-for></div></sc-if>
<sc-if value="{{{{hasSource}}}}" hint-placeholder-val="{{{{false}}}}"><p style="margin: 0; font-size: 12px; color: #5F6B7A">Regulatory source: <a href="{{{{sSource}}}}">FDA, Drug Supply Chain Security Act</a></p></sc-if>
<details style="border-top: 1px solid #E2E6EC; padding-top: 10px"><summary style="cursor: pointer; font-size: 13px; font-weight: 600; min-height: 32px">How the agents run it</summary>
<pre style="margin: 8px 0 0; padding: 12px; border-radius: 10px; background: #0F1720; color: #D7E0EA; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 12px; line-height: 18px; overflow-x: auto; white-space: pre">{{{{sYaml}}}}</pre></details>
</article>
</sc-if>
</div>

<section aria-label="Autonomy matrix" style="display: flex; flex-direction: column; gap: 10px; padding: 20px; {CARD}">
<h2 style="margin: 0; font-size: 16px; font-weight: 600">Autonomy matrix</h2>
<p style="margin: 0; font-size: 13px; color: #4B5563">Which policies an agent runs on its own, which need a person above a limit, and which a person always decides. Changing a level needs two approvals (AG-001).</p>
<div style="overflow-x: auto"><table style="width: 100%; border-collapse: collapse; font-size: 13px">
<thead><tr>
<th scope="col" style="text-align: left; padding: 8px 10px; border-bottom: 1px solid #E2E6EC; font-size: 12px; color: #5F6B7A">Policy</th>
<th scope="col" style="text-align: left; padding: 8px 10px; border-bottom: 1px solid #E2E6EC; font-size: 12px; color: #5F6B7A">Agent</th>
<th scope="col" style="text-align: center; padding: 8px 10px; border-bottom: 1px solid #E2E6EC; font-size: 12px; color: #1D47B8">A · Agent decides</th>
<th scope="col" style="text-align: center; padding: 8px 10px; border-bottom: 1px solid #E2E6EC; font-size: 12px; color: #5B2DA8">B · Person approves above limit</th>
<th scope="col" style="text-align: center; padding: 8px 10px; border-bottom: 1px solid #E2E6EC; font-size: 12px; color: #7A3B00">H · Person decides</th></tr></thead>
<tbody><sc-for list="{{{{matrix}}}}" as="m" hint-placeholder-count="8"><tr>
<td style="padding: 8px 10px; border-bottom: 1px solid #F1F3F6"><span title="{{{{m.tip}}}}" tabindex="0" style="{CHIP}">{{{{m.id}}}}</span> {{{{m.title}}}}</td>
<td style="padding: 8px 10px; border-bottom: 1px solid #F1F3F6">{{{{m.agent}}}}</td>
<td style="padding: 8px 10px; border-bottom: 1px solid #F1F3F6; text-align: center; color: #1D47B8">{{{{m.a}}}}</td>
<td style="padding: 8px 10px; border-bottom: 1px solid #F1F3F6; text-align: center; color: #5B2DA8">{{{{m.b}}}}</td>
<td style="padding: 8px 10px; border-bottom: 1px solid #F1F3F6; text-align: center; color: #7A3B00">{{{{m.h}}}}</td></tr></sc-for></tbody>
</table></div>
</section>'''

write("Policy.dc.html", page("Policy.dc.html", "Policy studio", PBODY,
      js_class({"policies": pols, "folders": [{"key": k, "name": v} for k, v in FOLDERS]}, PJS), 2100))

# ------------------------------------------------------------------ Agents
def A(name, group, what, model, uses, stops, metric, version="v2.4"):
    return dict(name=name, group=group, what=what, model=model, uses=uses, stops=stops, metric=metric, version=version,
                policies=[p["id"] for p in POL["policies"] if p["agent"] == name])

AGENTS = [
 A("Orchestrator", "Orchestration", "Routes each request through the agents and applies the autonomy matrix.", "Rules, plus a reasoning model for exceptions", "Durable Functions, event bus", "When a stage fails twice, or no policy applies", "260 requests · 0 stuck", "v3.1"),
 A("Intake", "Core MDM", "Reads emails, threads, PDFs and forms and turns them into key values mapped to the data model.", "Document extraction, plus a fast model", "Onboarding inbox, uploaded email files, document store", "Any field below 0.95", "95.4% auto"),
 A("Search before create", "Core MDM", "Looks for the party in the hub before anything new is made.", "Embeddings and fuzzy matching", "Search index over Business ready records and cross-references", "Never. Near-matches go to match & merge.", "34 duplicates stopped"),
 A("Match & merge", "Core MDM", "Scores candidates and applies survivorship to pick each winning value.", "Reasoning model with match rules", "Business ready record store", "Scores from 0.80 to 0.95", "94.6% auto · 2 overrides"),
 A("Enrichment", "Core MDM", "Adds D&B firmographics and family trees and LexisNexis business checks.", "Fast model", "D&B Direct+, LexisNexis", "D&B confidence code below 8", "97.3% auto"),
 A("Validation", "Core MDM", "Checks address, bank account, tax ID, licenses and exclusion lists.", "Rules, plus a fast model for name matching", "Address and account validation, IRS TIN match, DEA, state boards; OFAC, OIG, SAM", "Name match from 0.80, or account validation AMBER/RED", "91.0% auto"),
 A("Legal", "Function", "Decides on agreements, licensure and controlled-substance eligibility from documented policy.", "Rules engine; a reasoning model writes the explanation", "Policy store, contract repository, LexisNexis", "Edited terms, lapsed license, or no matching policy", "96.1% auto", "v1.2"),
 A("Procurement", "Function", "Sets pricing group and partner functions, and checks BPO supplier onboarding is complete.", "Rules engine", "Policy store, contracts, GPO rosters", "Contract without a pricing group; supplier information missing twice", "93.4% auto", "v1.2"),
 A("Credit", "Function", "Decides credit limit, payment terms and payment method.", "Rules engine with a scoring model", "Policy store, D&B scores, receivables", "Limit above $50,000; terms above the credit tier", "81.7% auto", "v1.3"),
 A("Tax", "Function", "Decides tax status from resale and exemption certificates.", "Rules engine; document extraction for certificates", "Policy store, certificate store", "Certificate missing, expired or in another name", "90.2% auto", "v1.1"),
 A("Steward copilot", "People support", "Explains each exception and recommends what to do.", "Reasoning model", "Audit trail and past steward decisions", "Always. It advises and never commits.", "53 of 61 recommendations accepted"),
 A("Lifecycle monitor", "People support", "Watches expiries, dormancy and D&B changes, and raises events.", "Rules and a nightly schedule", "Event bus, license feeds", "Deactivations and re-parenting", "27 events open"),
 A("Contextual outreach", "People support", "Drafts messages that draw on past conversations.", "Reasoning model", "CRM notes and email history, read-only", "Any message that cites a past conversation", "12 drafts · 9 sent unchanged"),
]

AJS = r'''
    const D = this.data();
    const sel = this.state.sel || 'Credit';
    const groups = D.groups.map((g) => ({ name: g.name, sub: g.sub, agents: D.agents.filter((a) => a.group === g.key).map((a) => ({
      name: a.name, what: a.what, metric: a.metric, pressed: a.name === sel ? 'true' : 'false',
      style: a.name === sel ? 'border-color: #1D47B8; box-shadow: 0 0 0 2px #9DB3EE' : 'border-color: #E2E6EC',
      pick: () => this.setState({ sel: a.name, editing: false, submitted: false }) })) }));
    const a = D.agents.find((x) => x.name === sel);
    const ov = (this.state.ov || {})[sel] || {};
    return {
      groups, count: D.agents.length, aName: a.name, aWhat: a.what, aModel: ov.model || a.model, aVersion: a.version, aUses: a.uses,
      aStops: ov.stops || a.stops, aMetric: a.metric,
      aPolicies: a.policies.map((id) => ({ id, tip: this.tip(id) })), hasPolicies: a.policies.length > 0,
      editing: !!this.state.editing, notEditing: !this.state.editing, submitted: !!this.state.submitted,
      startEdit: () => this.setState({ editing: true, dModel: ov.model || a.model, dStops: ov.stops || a.stops }),
      dModel: this.state.dModel || '', dStops: this.state.dStops || '',
      onModel: (e) => this.setState({ dModel: e.target.value }), onStops: (e) => this.setState({ dStops: e.target.value }),
      submit: () => { const o = Object.assign({}, this.state.ov || {}); o[sel] = { model: this.state.dModel, stops: this.state.dStops }; this.setState({ ov: o, editing: false, submitted: true }); },
      cancel: () => this.setState({ editing: false }),
    };
'''

ABODY = f'''{title_block("Platform / Agents", "Agents", "13 agents. Core MDM agents build the record; Legal, Procurement, Credit and Tax decide from documented policy; when no policy applies, the request goes to a person. Select an agent to see and change its settings.")}
<div style="display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start">
<div style="flex: 999 1 560px; min-width: 0; display: flex; flex-direction: column; gap: 18px">
<sc-for list="{{{{groups}}}}" as="g" hint-placeholder-count="3">
<section style="display: flex; flex-direction: column; gap: 10px">
<div style="display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px 14px"><h2 style="margin: 0; font-size: 16px; font-weight: 600">{{{{g.name}}}}</h2><span style="font-size: 13px; color: #5F6B7A">{{{{g.sub}}}}</span></div>
<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(min(220px, 100%), 1fr)); gap: 12px">
<sc-for list="{{{{g.agents}}}}" as="a" hint-placeholder-count="4">
<button type="button" aria-pressed="{{{{a.pressed}}}}" onClick="{{{{a.pick}}}}" style="display: flex; flex-direction: column; align-items: flex-start; gap: 6px; padding: 14px; border-radius: 14px; border: 1px solid; background: #FFFFFF; font-family: inherit; text-align: left; cursor: pointer; {{{{a.style}}}}">
<span style="display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 600; color: #0E5A32"><span aria-hidden="true" style="width: 8px; height: 8px; border-radius: 50%; background: #1E8A4C"></span>Healthy</span>
<span style="font-size: 15px; font-weight: 600; color: #131820">{{{{a.name}}}}</span>
<span style="font-size: 13px; line-height: 19px; color: #4B5563">{{{{a.what}}}}</span>
<span style="font-size: 12px; font-weight: 600; color: #1D47B8">{{{{a.metric}}}}</span>
</button>
</sc-for>
</div>
</section>
</sc-for>
</div>

<aside aria-label="Agent settings" style="flex: 1 1 340px; min-width: 0; display: flex; flex-direction: column; gap: 12px; padding: 20px; {CARD}">
<span style="font-size: 12px; color: #5F6B7A">Settings · {{{{aVersion}}}}</span>
<h2 style="margin: 0; font-size: 20px; font-weight: 600">{{{{aName}}}}</h2>
<p style="margin: 0; font-size: 13px; line-height: 20px; color: #2B323C">{{{{aWhat}}}}</p>
<sc-if value="{{{{notEditing}}}}" hint-placeholder-val="{{{{true}}}}">
<dl style="margin: 0; display: flex; flex-direction: column; gap: 10px; font-size: 13px">
<div><dt style="font-size: 12px; color: #5F6B7A">Model</dt><dd style="margin: 0">{{{{aModel}}}}</dd></div>
<div><dt style="font-size: 12px; color: #5F6B7A">Uses</dt><dd style="margin: 0">{{{{aUses}}}}</dd></div>
<div><dt style="font-size: 12px; color: #5F6B7A">Stops for a person</dt><dd style="margin: 0">{{{{aStops}}}}</dd></div>
<div><dt style="font-size: 12px; color: #5F6B7A">Last 30 days</dt><dd style="margin: 0">{{{{aMetric}}}}</dd></div>
</dl>
<sc-if value="{{{{hasPolicies}}}}" hint-placeholder-val="{{{{true}}}}"><div style="display: flex; flex-wrap: wrap; align-items: center; gap: 6px"><span style="font-size: 12px; color: #5F6B7A; flex-basis: 100%">Policies it runs</span><sc-for list="{{{{aPolicies}}}}" as="pp"><span title="{{{{pp.tip}}}}" tabindex="0" style="{CHIP}">{{{{pp.id}}}}</span></sc-for></div></sc-if>
<sc-if value="{{{{submitted}}}}" hint-placeholder-val="{{{{false}}}}"><p role="status" style="margin: 0; padding: 10px 12px; border-radius: 9px; background: #F1ECFB; color: #5B2DA8; font-size: 12px">Change submitted. It takes effect after a governance reviewer approves it (AG-001).</p></sc-if>
<button type="button" onClick="{{{{startEdit}}}}" style="{BTN}; align-self: flex-start">Edit settings</button>
</sc-if>
<sc-if value="{{{{editing}}}}" hint-placeholder-val="{{{{false}}}}">
<label for="ag-model" style="font-size: 12px; color: #5F6B7A">Model</label>
<input id="ag-model" value="{{{{dModel}}}}" onChange="{{{{onModel}}}}" style="height: 44px; box-sizing: border-box; padding: 0 12px; border: 1px solid #CDD3DC; border-radius: 9px; font-family: inherit; font-size: 14px">
<label for="ag-stops" style="font-size: 12px; color: #5F6B7A">Stops for a person (guardrail)</label>
<textarea id="ag-stops" value="{{{{dStops}}}}" onChange="{{{{onStops}}}}" rows="3" style="box-sizing: border-box; padding: 10px 12px; border: 1px solid #CDD3DC; border-radius: 9px; font-family: inherit; font-size: 14px"></textarea>
<p style="margin: 0; font-size: 12px; color: #5F6B7A">Thresholds come from the policy store. Changing them here opens a policy draft.</p>
<div style="display: flex; flex-wrap: wrap; gap: 8px"><button type="button" onClick="{{{{submit}}}}" style="{BTN_DARK}">Submit for approval</button><button type="button" onClick="{{{{cancel}}}}" style="{BTN}">Cancel</button></div>
</sc-if>
</aside>
</div>'''

GROUPS = [{"key": "Orchestration", "name": "Orchestration", "sub": "Runs the flow"},
          {"key": "Core MDM", "name": "Core MDM agents", "sub": "Build the Business ready record"},
          {"key": "Function", "name": "Function agents", "sub": "Decide from documented policy"},
          {"key": "People support", "name": "Steward and lifecycle", "sub": "Help people and watch records over time"}]
write("Agents.dc.html", page("Agents.dc.html", "Agents", ABODY, js_class({"agents": AGENTS, "groups": GROUPS}, AJS), 1700))
print("policy+agents ok")
