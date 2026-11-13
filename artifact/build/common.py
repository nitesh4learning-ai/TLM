"""Shared shell, navigation and detail-panel pieces for the Agentic MDM screens."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ART = os.path.dirname(HERE)
REPO = os.path.dirname(ART)

POL = json.load(open(os.path.join(REPO, "policies", "policies.json")))
LEVELS = POL["levels"]
POLICY_MAP = {p["id"]: {"title": p["title"], "level": p["level"], "agent": p["agent"], "folder": p["folder"]} for p in POL["policies"]}

ICON = {
    "tower": '<path d="M4 18a8 8 0 1 1 16 0"></path><path d="M12 18l4-6"></path>',
    "intake": '<path d="M4 13l2-7h12l2 7"></path><path d="M4 13v5h16v-5h-5a3 3 0 0 1-6 0H4z"></path>',
    "steward": '<circle cx="12" cy="8" r="3.5"></circle><path d="M5 20c1-3.8 3.8-6 7-6s6 2.2 7 6"></path>',
    "bell": '<path d="M6 16v-5a6 6 0 1 1 12 0v5l1.5 2h-15z"></path><path d="M10 20.5a2 2 0 0 0 4 0"></path>',
    "journey": '<circle cx="6" cy="6" r="2.5"></circle><circle cx="18" cy="18" r="2.5"></circle><path d="M8.5 6H15a3.5 3.5 0 0 1 0 7H9a3.5 3.5 0 0 0 0 7h6.5"></path>',
    "record": '<rect x="4" y="3" width="16" height="18" rx="2"></rect><path d="M8 8h8M8 12h8M8 16h5"></path>',
    "tree": '<rect x="9" y="3" width="6" height="5" rx="1"></rect><rect x="3" y="16" width="6" height="5" rx="1"></rect><rect x="15" y="16" width="6" height="5" rx="1"></rect><path d="M12 8v4M6 16v-4h12v4"></path>',
    "agents": '<rect x="6" y="6" width="12" height="12" rx="2"></rect><path d="M9 2.5V6M15 2.5V6M9 18v3.5M15 18v3.5M2.5 9H6M2.5 15H6M18 9h3.5M18 15h3.5"></path>',
    "policy": '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z"></path><path d="M9 11h6M9 14.5h4"></path>',
}

NAV = [
    ("item", "Main.dc.html", "tower", "Control tower", None),
    ("head", "Work"),
    ("item", "Intake.dc.html", "intake", "Intake", None),
    ("item", "Steward.dc.html", "steward", "Steward queue", "12"),
    ("item", "Lifecycle.dc.html", "bell", "Lifecycle &amp; outreach", "7"),
    ("head", "Records"),
    ("item", "Journey.dc.html", "journey", "Request journey", None),
    ("item", "Records.dc.html", "record", "Business ready records", None),
    ("item", "Hierarchy.dc.html", "tree", "Hierarchies", None),
    ("head", "Platform"),
    ("item", "Agents.dc.html", "agents", "Agents", None),
    ("item", "Policy.dc.html", "policy", "Policy studio", None),
]

IT = "flex: 1 1 180px; display: flex; align-items: center; gap: 10px; height: 44px; box-sizing: border-box; padding: 0 12px; border-radius: 9px; text-decoration: none; font-size: 14px; "


def nav(active):
    out = ['<nav aria-label="Main" style="flex: 1 1 224px; display: flex; flex-wrap: wrap; align-content: flex-start; gap: 2px; padding: 20px 12px; box-sizing: border-box; background: #FFFFFF; border-right: 1px solid #E2E6EC">']
    for n in NAV:
        if n[0] == "head":
            out.append(f'<div style="flex: 1 1 100%; padding: 16px 12px 6px; font-size: 11px; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; color: #5F6B7A">{n[1]}</div>')
            continue
        _, href, icon, label, badge = n
        on = href == active
        st = IT + ("font-weight: 600; color: #1D47B8; background: #EAF0FE" if on else "font-weight: 500; color: #4B5563")
        cur = ' aria-current="page"' if on else ""
        b = f'<span style="font-size: 12px; font-weight: 600; color: #9A4A00; background: #FFF1DE; border-radius: 999px; padding: 1px 8px">{badge}</span>' if badge else ""
        out.append(f'<a href="{href}"{cur} style="{st}"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICON[icon]}</svg><span style="flex: 1">{label}</span>{b}</a>')
    out.append("</nav>")
    return "\n".join(out)


def header(slug):
    return f'''<header style="display: flex; flex-wrap: wrap; align-items: center; gap: 12px 20px; padding: 12px 24px; background: #FFFFFF; border-bottom: 1px solid #E2E6EC">
<a href="Main.dc.html" style="display: flex; align-items: center; gap: 10px; text-decoration: none; color: #131820">
<span style="display: flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 9px; background: #131820"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"></path></svg></span>
<span style="font-family: 'Space Grotesk', Inter, sans-serif; font-weight: 600; font-size: 17px; letter-spacing: -0.01em">Agentic MDM</span>
</a>
<div style="flex: 1 1 260px; max-width: 520px; display: flex; align-items: center; gap: 8px; height: 44px; box-sizing: border-box; padding: 0 12px; background: #F6F7F9; border: 1px solid #E2E6EC; border-radius: 10px">
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#5F6B7A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="6.5"></circle><path d="M20 20l-4-4"></path></svg>
<label for="search-{slug}" style="position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap">Search</label>
<input id="search-{slug}" type="search" placeholder="Search customers, suppliers, DUNS, DEA or request ID" style="flex: 1; min-width: 0; border: 0; background: transparent; font-family: inherit; font-size: 14px; color: #131820; outline: none">
</div>
<div style="display: flex; align-items: center; gap: 10px; margin-left: auto">
<label for="persona-{slug}" style="font-size: 12px; color: #5F6B7A">Viewing as</label>
<select id="persona-{slug}" style="height: 44px; border: 1px solid #CDD3DC; border-radius: 9px; background: #FFFFFF; font-family: inherit; font-size: 13px; padding: 0 10px; color: #131820">
<option>Data steward</option><option>Governance lead</option><option>Requester · Sales ops</option><option>Customer care</option><option>Platform admin</option>
</select>
<span aria-hidden="true" style="display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: 50%; background: #EAF0FE; color: #1D47B8; font-size: 12px; font-weight: 600">JO</span>
</div>
</header>'''


def page(file, title, body, js, height):
    slug = file.split(".")[0].lower()
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title} · Agentic MDM</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@400;500&amp;family=Space+Grotesk:wght@500;600&amp;display=swap" rel="stylesheet">
<style>
body{{margin:0;font-family:Inter,"Segoe UI",system-ui,-apple-system,sans-serif;color:#131820;background:#F6F7F9;-webkit-font-smoothing:antialiased}}
a{{color:#1F4FC8}}a:hover{{color:#163B99}}
</style>
</helmet>
<div style="min-height: 100vh; display: flex; flex-direction: column; background: #F6F7F9; font-family: Inter, 'Segoe UI', system-ui, sans-serif; color: #131820">
{header(slug)}
<div style="flex: 1 0 auto; display: flex; flex-wrap: wrap">
{nav(file)}
<main style="flex: 999 1 560px; min-width: 0; box-sizing: border-box; padding: 28px 32px 56px; display: flex; flex-direction: column; gap: 24px">
{body}
</main>
</div>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":1440,"height":{height}}}}}'>
{js}
</script>
</body>
</html>
'''


def title_block(eyebrow, h1, sub):
    return f'''<div style="display: flex; flex-direction: column; gap: 6px; min-width: 0">
<div style="font-size: 13px; line-height: 18px; color: #5F6B7A">{eyebrow}</div>
<h1 style="margin: 0; font-family: 'Space Grotesk', Inter, sans-serif; font-size: 30px; line-height: 36px; font-weight: 600; letter-spacing: -0.02em">{h1}</h1>
<p style="margin: 0; max-width: 760px; font-size: 14px; line-height: 21px; color: #4B5563">{sub}</p>
</div>'''


CARD = "background: #FFFFFF; border: 1px solid #E2E6EC; border-radius: 14px"
CHIP = "display: inline-flex; align-items: center; height: 22px; padding: 0 8px; border-radius: 6px; background: #F1F3F6; border: 1px solid #E2E6EC; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 11px; color: #2B323C; cursor: help; white-space: nowrap"
BTN = "display: inline-flex; align-items: center; gap: 6px; height: 44px; box-sizing: border-box; padding: 0 14px; border-radius: 9px; border: 1px solid #CDD3DC; background: #FFFFFF; color: #131820; font-family: inherit; font-size: 13px; font-weight: 600; cursor: pointer"
BTN_DARK = "display: inline-flex; align-items: center; gap: 6px; height: 44px; box-sizing: border-box; padding: 0 16px; border-radius: 9px; border: 0; background: #131820; color: #FFFFFF; font-family: inherit; font-size: 13px; font-weight: 600; cursor: pointer; text-decoration: none"
MORE = "align-self: flex-start; display: inline-flex; align-items: center; gap: 8px; height: 44px; box-sizing: border-box; padding: 0 14px; border-radius: 9px; border: 1px dashed #9DB3EE; background: #F5F8FF; color: #1D47B8; font-family: inherit; font-size: 13px; font-weight: 600; cursor: pointer"

# A section renderer: sections carry kind text | kv | table | checks; cells/rows may carry a policy chip
SECTIONS = f'''<sc-for list="{{{{visible}}}}" as="sec" hint-placeholder-count="2">
<section style="display: flex; flex-direction: column; gap: 10px; padding: 16px; {CARD}">
<div style="display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 8px">
<h3 style="margin: 0; font-size: 14px; line-height: 20px; font-weight: 600">{{{{sec.title}}}}</h3>
<span style="font-size: 12px; color: #5F6B7A">{{{{sec.meta}}}}</span>
</div>
<sc-if value="{{{{sec.isText}}}}" hint-placeholder-val="{{{{false}}}}"><p style="margin: 0; font-size: 13px; line-height: 20px; color: #2B323C; white-space: pre-line">{{{{sec.text}}}}</p></sc-if>
<sc-if value="{{{{sec.isKv}}}}" hint-placeholder-val="{{{{true}}}}">
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(min(240px, 100%), 1fr)); gap: 10px 20px">
<sc-for list="{{{{sec.rows}}}}" as="r" hint-placeholder-count="4">
<div style="display: flex; flex-direction: column; gap: 2px; min-width: 0">
<span style="font-size: 12px; color: #5F6B7A">{{{{r.k}}}}</span>
<span style="font-size: 14px; line-height: 20px; color: #131820; overflow-wrap: anywhere">{{{{r.v}}}}</span>
<span style="display: flex; flex-wrap: wrap; align-items: center; gap: 6px; font-size: 12px; color: #5F6B7A">{{{{r.note}}}}<sc-if value="{{{{r.policy}}}}" hint-placeholder-val="{{{{false}}}}"><span title="{{{{r.tip}}}}" tabindex="0" style="{CHIP}">{{{{r.policy}}}}</span></sc-if></span>
</div>
</sc-for>
</div>
</sc-if>
<sc-if value="{{{{sec.isTable}}}}" hint-placeholder-val="{{{{false}}}}">
<div style="overflow-x: auto">
<table style="width: 100%; border-collapse: collapse; font-size: 13px; line-height: 19px">
<thead><tr><sc-for list="{{{{sec.cols}}}}" as="c"><th scope="col" style="text-align: left; padding: 8px 10px; border-bottom: 1px solid #E2E6EC; font-size: 12px; font-weight: 600; color: #5F6B7A; white-space: nowrap">{{{{c.v}}}}</th></sc-for></tr></thead>
<tbody><sc-for list="{{{{sec.rows}}}}" as="r"><tr style="{{{{r.style}}}}"><sc-for list="{{{{r.cells}}}}" as="c"><td style="padding: 8px 10px; border-bottom: 1px solid #F1F3F6; vertical-align: top; {{{{c.style}}}}">{{{{c.v}}}}<sc-if value="{{{{c.policy}}}}" hint-placeholder-val="{{{{false}}}}"> <span title="{{{{c.tip}}}}" tabindex="0" style="{CHIP}">{{{{c.policy}}}}</span></sc-if></td></sc-for></tr></sc-for></tbody>
</table>
</div>
</sc-if>
<sc-if value="{{{{sec.isChecks}}}}" hint-placeholder-val="{{{{false}}}}">
<ul style="margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 6px">
<sc-for list="{{{{sec.rows}}}}" as="r">
<li style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 9px; {{{{r.style}}}}">
<span style="font-size: 12px; font-weight: 700; min-width: 64px">{{{{r.mark}}}}</span>
<span style="flex: 1 1 260px; font-size: 13px; line-height: 19px">{{{{r.k}}}}<span style="color: #5F6B7A"> · {{{{r.note}}}}</span></span>
<sc-if value="{{{{r.policy}}}}" hint-placeholder-val="{{{{false}}}}"><span title="{{{{r.tip}}}}" tabindex="0" style="{CHIP}">{{{{r.policy}}}}</span></sc-if>
</li>
</sc-for>
</ul>
</sc-if>
</section>
</sc-for>
<sc-if value="{{{{hasMore}}}}" hint-placeholder-val="{{{{true}}}}"><button type="button" onClick="{{{{more}}}}" style="{MORE}"><span aria-hidden="true" style="font-size: 18px; line-height: 1">…</span>{{{{moreLabel}}}}</button></sc-if>
<sc-if value="{{{{canLess}}}}" hint-placeholder-val="{{{{false}}}}"><button type="button" onClick="{{{{less}}}}" style="{BTN}">Show less</button></sc-if>'''

# JS helper shared by pages: turns raw sections into renderable ones
JS_HELPERS = r'''
  tip(id) {
    const p = this.policies()[id];
    if (!p) return id;
    return id + ' · ' + p.title + ' · Autonomy ' + p.level + ' (' + this.levels()[p.level] + ') · Agent: ' + p.agent;
  }
  prepRow(r, kind) {
    const out = Object.assign({}, r);
    out.policy = r.policy || '';
    out.tip = r.policy ? this.tip(r.policy) : '';
    if (kind === 'table') {
      out.cells = (r.cells || []).map((c) => {
        const cell = typeof c === 'object' && c !== null ? Object.assign({}, c) : { v: c };
        cell.v = cell.v === undefined || cell.v === null ? '' : String(cell.v);
        cell.policy = cell.policy || '';
        cell.tip = cell.policy ? this.tip(cell.policy) : '';
        cell.style = cell.win ? 'background: #EAF0FE; color: #1D47B8; font-weight: 600' : (cell.style || '');
        return cell;
      });
      out.style = r.style || '';
    }
    if (kind === 'checks') {
      const pass = r.pass === true, human = r.pass === 'human';
      out.mark = pass ? '✓ Passed' : (human ? '● Person' : '✕ Failed');
      out.style = pass ? 'background: #EEF7F1; color: #0E5A32' : (human ? 'background: #FFF1DE; color: #7A3B00' : 'background: #FDECEC; color: #8A1C1C');
      out.note = r.note || '';
    }
    out.note = out.note || '';
    return out;
  }
  prep(sections, depth) {
    const all = (sections || []).map((s) => ({
      title: s.title, meta: s.meta || '', level: s.level || 1, text: s.text || '',
      isText: s.kind === 'text', isKv: s.kind === 'kv', isTable: s.kind === 'table', isChecks: s.kind === 'checks',
      cols: (s.cols || []).map((c) => ({ v: c })),
      rows: (s.rows || []).map((r) => this.prepRow(r, s.kind)),
    }));
    const maxLevel = all.reduce((m, s) => Math.max(m, s.level), 1);
    return { visible: all.filter((s) => s.level <= depth), hasMore: depth < maxLevel, canLess: depth > 1 && depth >= maxLevel, maxLevel };
  }
'''


def js_class(data_obj, body, extra=""):
    data = json.dumps(data_obj, ensure_ascii=False)
    pol = json.dumps(POLICY_MAP, ensure_ascii=False)
    lev = json.dumps(LEVELS, ensure_ascii=False)
    return f'''class Component extends DCLogic {{
  constructor(props) {{ super(props); this.state = {{}}; }}
  data() {{ return {data}; }}
  policies() {{ return {pol}; }}
  levels() {{ return {lev}; }}
{JS_HELPERS}
{extra}
  renderVals() {{
{body}
  }}
}}'''


def replace_nav(html, file):
    return re.sub(r'<nav aria-label="Main".*?</nav>', lambda m: nav(file), html, count=1, flags=re.S)


def write(file, text):
    open(os.path.join(ART, file), "w").write(text)
