import React, { useEffect, useMemo, useState } from 'react';
import { api, go } from '../api.js';
import { Title, Sections, useLoad, Err } from '../components.jsx';

const KIND_COLOR = { 'Ultimate parent': '#131820', 'Regional system': '#1D47B8', Hospital: '#2F5FE0', Pharmacy: '#0E7C66', Infusion: '#6D3FC0',
  'Surgery center': '#B45309', 'Long-term care': '#9A3412', 'Ship-to': '#8A94A3' };
const color = (k) => KIND_COLOR[k] || '#2F5FE0';

/** Radial network layout: root in the middle, each level on its own ring, leaves spread by subtree size. */
function layout(nodes, kids) {
  const root = nodes.find((n) => !n.parent);
  if (!root) return {};
  const leaves = {};
  const count = (id) => { const k = kids[id] || []; leaves[id] = k.length ? k.reduce((a, c) => a + count(c), 0) : 1; return leaves[id]; };
  count(root.id);
  const maxLevel = Math.max(...nodes.map((n) => n.level));
  const ring = maxLevel ? 380 / maxLevel : 0;
  const pos = {};
  const place = (id, a0, a1, depth) => {
    const a = (a0 + a1) / 2;
    pos[id] = { x: depth ? Math.cos(a) * depth * ring : 0, y: depth ? Math.sin(a) * depth * ring : 0, a };
    let cur = a0;
    (kids[id] || []).forEach((c) => { const span = ((a1 - a0) * leaves[c]) / leaves[id]; place(c, cur, cur + span, depth + 1); cur += span; });
  };
  place(root.id, -Math.PI, Math.PI, 0);
  return pos;
}

function Network({ nodes, kids, sel, onSel }) {
  const pos = useMemo(() => layout(nodes, kids), [nodes, kids]);
  const R = 470;
  return (
    <div className="netwrap">
      <svg viewBox={`${-R} ${-R} ${2 * R} ${2 * R}`} width="100%" style={{ display: 'block', minWidth: 640, height: 'auto' }} role="img" aria-label="Network view of the corporate family">
        {[1, 2, 3].map((i) => <circle key={i} r={(380 / 3) * i} fill="none" stroke="#E2E6EC" strokeDasharray="3 6" />)}
        {nodes.filter((n) => n.parent && pos[n.id] && pos[n.parent]).map((n) => {
          const a = pos[n.parent], b = pos[n.id];
          const on = sel === n.id || sel === n.parent;
          return <path key={'l' + n.id} d={`M${a.x},${a.y} Q${(a.x + b.x) / 2 * 0.9},${(a.y + b.y) / 2 * 0.9} ${b.x},${b.y}`} fill="none" stroke={on ? '#1D47B8' : '#C9D1DD'} strokeWidth={on ? 2.2 : 1.2} />;
        })}
        {nodes.filter((n) => pos[n.id]).map((n) => {
          const p = pos[n.id]; const r = n.level === 0 ? 16 : n.level === 1 ? 12 : n.level === 2 ? 9 : 5;
          const isSel = sel === n.id;
          const showLabel = n.level <= 2 || isSel;
          const right = Math.cos(p.a) >= 0;
          return (
            <g key={n.id} transform={`translate(${p.x},${p.y})`} onClick={() => onSel(n.id)} style={{ cursor: 'pointer' }} tabIndex={0} role="button" aria-label={n.name}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSel(n.id); }}>
              {isSel && <circle r={r + 7} fill="none" stroke="#131820" strokeWidth="2" />}
              <circle r={r} fill={n.status === 'Proposed' ? '#FFF1DE' : color(n.kind)} stroke={n.status === 'Proposed' ? '#D97706' : '#fff'} strokeWidth="2" strokeDasharray={n.status === 'Proposed' ? '3 2' : ''} />
              {showLabel && (
                <text x={n.level === 0 ? 0 : right ? r + 6 : -(r + 6)} y={n.level === 0 ? r + 18 : 4} textAnchor={n.level === 0 ? 'middle' : right ? 'start' : 'end'}
                  fontSize={n.level === 0 ? 14 : n.level === 1 ? 12 : 10.5} fontWeight={n.level <= 1 || isSel ? 600 : 500} fill="#131820"
                  style={{ paintOrder: 'stroke', stroke: '#fff', strokeWidth: 3 }}>
                  {n.name.length > 34 && !isSel ? n.name.slice(0, 32) + '…' : n.name}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function Tree({ nodes, kids, byId, sel, onSel }) {
  const [exp, setExp] = useState(() => Object.fromEntries(nodes.filter((n) => n.level < 1).map((n) => [n.id, true])));
  useEffect(() => { // open the path to the selected node
    if (!sel) return; const e = { ...exp }; let p = byId[sel] && byId[sel].parent; while (p) { e[p] = true; p = byId[p] && byId[p].parent; } setExp(e);
  }, [sel]); // eslint-disable-line
  const visible = nodes.filter((n) => { let p = n.parent; while (p) { if (!exp[p]) return false; p = byId[p] && byId[p].parent; } return true; });
  const toggle = (id) => setExp({ ...exp, [id]: !exp[id] });
  return (
    <div className="stack" style={{ gap: 8 }}>
      <div className="row" style={{ gap: 8 }}>
        <button type="button" className="btn" onClick={() => setExp(Object.fromEntries(nodes.filter((x) => kids[x.id]).map((x) => [x.id, true])))}>Expand all</button>
        <button type="button" className="btn" onClick={() => setExp({ [nodes[0].id]: true })}>Collapse</button>
      </div>
      <ul className="tree" role="tree">
        {visible.map((x) => (
          <li key={x.id} role="treeitem" aria-expanded={kids[x.id] ? !!exp[x.id] : undefined} style={{ paddingLeft: x.level * 22 }}>
            {kids[x.id] ? <button type="button" className="tg" aria-label={(exp[x.id] ? 'Collapse ' : 'Expand ') + x.name} onClick={() => toggle(x.id)}>{exp[x.id] ? '−' : '+'}</button> : <span style={{ width: 32 }} />}
            <button type="button" className={'node' + (x.id === sel ? ' on' : x.status === 'Proposed' ? ' proposed' : '')} onClick={() => onSel(x.id)} onDoubleClick={() => kids[x.id] && toggle(x.id)}>
              <span aria-hidden="true" style={{ width: 10, height: 10, borderRadius: '50%', background: color(x.kind), alignSelf: 'center' }} />
              <strong style={{ fontSize: 13 }}>{x.name}</strong><span className="small muted">{x.kind}</span>{x.status === 'Proposed' && <span className="small">Proposed</span>}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Search() {
  const [q, setQ] = useState('');
  const res = useLoad(() => api.get('/hierarchies/search?q=' + encodeURIComponent(q)), [q]);
  return (
    <>
      <Title eyebrow="Business ready record" title="Hierarchy search">Search a company, a brand or a DUNS number, then open its corporate family as a network or a tree.</Title>
      <section className="card">
        <label className="lbl" htmlFor="hq">Search</label>
        <input id="hq" type="search" autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. bra, Brazos, Cedar Park, 61-203" style={{ height: 52, fontSize: 16 }} />
        <span className="small muted">{res.data ? `${res.data.length} match${res.data.length === 1 ? '' : 'es'}` : ''}</span>
        <div className="stack" style={{ gap: 8 }}>
          {(res.data || []).map((x) => (
            <button type="button" key={x.familyId + x.id} className="result" onClick={() => go(`hierarchy/${encodeURIComponent(x.familyId)}~${encodeURIComponent(x.id)}`)}>
              <span style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <span aria-hidden="true" style={{ width: 12, height: 12, borderRadius: '50%', background: color(x.kind) }} />
                <span style={{ display: 'flex', flexDirection: 'column', gap: 2 }}><strong>{x.name}</strong><span className="small muted">{x.kind}{x.city ? ' · ' + x.city : ''} · Family: {x.family}</span></span>
              </span>
              <span className="small" style={{ color: 'var(--blue)', fontWeight: 600 }}>Open hierarchy →</span>
            </button>
          ))}
        </div>
      </section>
    </>
  );
}

export default function Hierarchy({ arg }) {
  if (!arg) return <Search />;
  const [fid, focus] = arg.split('~').map(decodeURIComponent);
  return <Family fid={fid} focus={focus} />;
}

function Family({ fid, focus }) {
  const h = useLoad(() => api.get('/hierarchies/' + encodeURIComponent(fid)), [fid]);
  const [view, setView] = useState('network');
  const [sel, setSel] = useState(focus || null);
  useEffect(() => setSel(focus || null), [focus]);
  const nodes = (h.data && h.data.nodes) || [];
  const byId = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n])), [nodes]);
  const kids = useMemo(() => { const k = {}; nodes.forEach((n) => { if (n.parent) (k[n.parent] = k[n.parent] || []).push(n.id); }); return k; }, [nodes]);
  const n = byId[sel] || nodes[0];
  const s = (h.data && h.data.summary) || {};
  const sections = n ? [
    { title: 'Key details', kind: 'kv', level: 1, rows: [
      { k: 'Type', v: n.kind }, { k: 'DUNS', v: n.duns || '—', note: n.duns ? 'D&B' : '' },
      { k: 'Location', v: n.address || [n.city, n.state].filter(Boolean).join(', ') || '—' },
      { k: 'Status', v: n.status, note: n.status === 'Proposed' ? 'In the D&B family tree; not yet in the hub' : '' },
      { k: 'Children', v: String((kids[n.id] || []).length) }] },
    ...(n.dea ? [{ title: 'Compliance', kind: 'kv', level: 2, rows: [
      { k: 'DEA', v: n.dea + ' · II–V', note: 'Active', policy: 'RG-CS-001' }, { k: 'State license', v: n.license, note: 'Active', policy: 'RG-CS-001' },
      { k: 'NPI', v: n.npi }, { k: 'Exclusion lists', v: 'OFAC, OIG, SAM clear', note: 'LexisNexis · test data', policy: 'AG-002' }] }] : []),
    ...((kids[n.id] || []).length ? [{ title: 'Children', kind: 'table', level: 3, cols: ['Name', 'Type', 'Status'],
      rows: (kids[n.id] || []).map((c) => ({ cells: [{ v: byId[c].name }, { v: byId[c].kind }, { v: byId[c].status }] })) }] : []),
  ] : [];
  return (
    <>
      <Title eyebrow={<><a href="#/records">Business ready records</a>{focus && String(focus).startsWith('BRR-') ? <> / <a href={'#/records/' + focus}>{focus}</a></> : n && n.recordId ? <> / <a href={'#/records/' + n.recordId}>{n.recordId}</a></> : null} / Hierarchy</>} title={nodes[0] ? nodes[0].name : 'Hierarchy'}
        right={<div className="seg" role="radiogroup" aria-label="View">
          <button type="button" role="radio" aria-checked={view === 'network'} className={view === 'network' ? 'on' : ''} onClick={() => setView('network')}>Network</button>
          <button type="button" role="radio" aria-checked={view === 'tree'} className={view === 'tree' ? 'on' : ''} onClick={() => setView('tree')}>Tree</button>
        </div>}>
        Corporate family from D&amp;B joined to the hub. Click any node to see its details.
      </Title>
      <Err error={h.error} />
      <div className="row small" style={{ alignItems: 'center' }}>
        <span className="pill"><strong>{s.legalEntities}</strong> legal entities</span><span className="pill"><strong>{s.shipToAccounts}</strong> ship-to accounts</span><span className="pill"><strong>{s.nodes}</strong> nodes</span>
        <a className="btn" href="#/records">← Back to records</a>
      </div>
      <div className="legend">{Object.entries(KIND_COLOR).map(([k, c]) => <span key={k}><i style={{ background: c }} />{k}</span>)}<span><i style={{ background: '#FFF1DE', border: '1px dashed #D97706' }} />Proposed</span></div>
      <div className="row">
        <section className="grow" style={{ flex: '2 1 560px' }} aria-label="Hierarchy">
          {nodes.length > 0 && (view === 'network' ? <Network nodes={nodes} kids={kids} sel={n && n.id} onSel={setSel} /> : <div className="card"><Tree nodes={nodes} kids={kids} byId={byId} sel={n && n.id} onSel={setSel} /></div>)}
        </section>
        {n && (
          <section className="stack" style={{ flex: '1 1 360px', minWidth: 0 }}>
            <div className="card"><span className="small muted">{n.kind}</span><h2>{n.name}</h2>
              {n.recordId && <a className="btn dark" style={{ alignSelf: 'flex-start' }} href={`#/records/${n.recordId}`}>Open Business ready record {n.recordId}</a>}</div>
            <Sections sections={sections} resetKey={n.id} />
          </section>
        )}
      </div>
    </>
  );
}
