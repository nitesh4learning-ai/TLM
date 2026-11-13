import React, { useMemo, useState } from 'react';
import { api } from '../api.js';
import { Title, Sections, useLoad, Err } from '../components.jsx';

export default function Hierarchy() {
  const h = useLoad(() => api.get('/hierarchy'), []);
  const [exp, setExp] = useState({ 'N-0001': true, 'N-0002': true });
  const [sel, setSel] = useState('N-0003');
  const nodes = (h.data && h.data.nodes) || [];
  const byId = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n])), [nodes]);
  const kids = useMemo(() => { const k = {}; nodes.forEach((n) => { (k[n.parent] = k[n.parent] || []).push(n.id); }); return k; }, [nodes]);
  const visible = nodes.filter((n) => { let p = n.parent; while (p) { if (!exp[p]) return false; p = byId[p] && byId[p].parent; } return true; });
  const toggle = (id) => setExp({ ...exp, [id]: !exp[id] });
  const n = byId[sel];
  const sections = n ? [
    { title: 'Key details', kind: 'kv', level: 1, rows: [
      { k: 'Type', v: n.kind }, { k: 'DUNS', v: n.duns || '—', note: n.duns ? 'D&B' : 'Ship-to, no DUNS' },
      { k: 'Location', v: n.address || `${n.city}, ${n.state}` },
      { k: 'Status', v: n.status, note: n.status === 'Proposed' ? 'In the D&B family tree; not yet in the hub' : '' },
      { k: 'Children', v: String((kids[n.id] || []).length) }] },
    ...(n.dea ? [{ title: 'Compliance', kind: 'kv', level: 2, rows: [
      { k: 'DEA', v: n.dea + ' · II–V', note: 'Active', policy: 'RG-CS-001' }, { k: 'State license', v: n.license, note: 'Active', policy: 'RG-CS-001' },
      { k: 'NPI', v: n.npi }, { k: 'Exclusion lists', v: 'OFAC, OIG, SAM clear', note: 'LexisNexis', policy: 'AG-002' }] }] : []),
    { title: 'Children', kind: 'table', level: 3, cols: ['Name', 'Type', 'Status'],
      rows: (kids[n.id] || []).map((c) => ({ cells: [{ v: byId[c].name }, { v: byId[c].kind }, { v: byId[c].status }] })) },
  ] : [];
  const s = (h.data && h.data.summary) || {};
  return (
    <>
      <Title eyebrow="Records / Hierarchies" title="Brazos Health System">Corporate family from D&amp;B joined to the hub. Click a node to see its details; double-click to expand or collapse it.</Title>
      <Err error={h.error} />
      <div className="row small">
        <span className="pill"><strong>{s.legalEntities}</strong> legal entities</span><span className="pill"><strong>{s.shipToAccounts}</strong> ship-to accounts</span><span className="pill"><strong>{s.nodes}</strong> nodes</span>
      </div>
      <div className="row">
        <section className="card grow" aria-label="Hierarchy" style={{ flex: '1 1 420px' }}>
          <div className="row" style={{ gap: 8 }}>
            <button type="button" className="btn" onClick={() => setExp(Object.fromEntries(nodes.filter((x) => kids[x.id]).map((x) => [x.id, true])))}>Expand all</button>
            <button type="button" className="btn" onClick={() => setExp({ 'N-0001': true })}>Collapse</button>
          </div>
          <ul className="tree" role="tree">
            {visible.map((x) => (
              <li key={x.id} role="treeitem" aria-expanded={kids[x.id] ? !!exp[x.id] : undefined} style={{ paddingLeft: x.level * 22 }}>
                {kids[x.id] ? <button type="button" className="tg" aria-label={(exp[x.id] ? 'Collapse ' : 'Expand ') + x.name} onClick={() => toggle(x.id)}>{exp[x.id] ? '−' : '+'}</button> : <span style={{ width: 32 }} />}
                <button type="button" className={'node' + (x.id === sel ? ' on' : x.status === 'Proposed' ? ' proposed' : '')} onClick={() => setSel(x.id)} onDoubleClick={() => kids[x.id] && toggle(x.id)}>
                  <strong style={{ fontSize: 13 }}>{x.name}</strong><span className="small muted">{x.kind}</span>{x.status === 'Proposed' && <span className="small">Proposed</span>}
                </button>
              </li>
            ))}
          </ul>
        </section>
        {n && (
          <section className="stack" style={{ flex: '1 1 420px', minWidth: 0 }}>
            <div className="card"><span className="small muted">{n.kind}</span><h2>{n.name}</h2>
              {n.recordId && <a className="btn dark" style={{ alignSelf: 'flex-start' }} href={`#/records/${n.recordId}`}>Open Business ready record {n.recordId}</a>}</div>
            <Sections sections={sections} resetKey={n.id} />
          </section>
        )}
      </div>
    </>
  );
}
