import React, { useState } from 'react';
import { api, go } from '../api.js';
import { Title, Sections, useLoad, Err } from '../components.jsx';

const money = (n) => (n || n === 0 ? '$' + Number(n).toLocaleString() : '—');
const W = (rec, attr) => (rec.winners || {})[attr] || [];

function build(rec) {
  const x = rec.crossReferences || [];
  const sys = {};
  x.forEach((c) => { sys[c.system] = (sys[c.system] || 0) + 1; });
  const sysText = Object.entries(sys).map(([k, v]) => `${v} ${k}`).join(', ');
  const sa = rec.salesAreas || [];
  const cell = (v, pol) => ({ v, policy: pol || '' });
  const sections = [
    { title: 'Key details', kind: 'kv', level: 1, rows: [
      { k: 'Legal name', v: rec.legalName, note: W(rec, 'legalName')[0] ? 'From ' + W(rec, 'legalName')[0] : '', policy: W(rec, 'legalName')[1] },
      { k: 'DUNS', v: rec.duns || '—', note: '' },
      { k: 'Address', v: rec.address, note: '', policy: W(rec, 'address')[1] },
      { k: 'Type', v: rec.type || '—', note: rec.parent ? 'Parent: ' + rec.parent : '' },
      { k: 'Sales areas', v: sa.map((s) => s.area).join(' · ') || '—', note: '' },
      { k: 'Cross-references', v: x.length ? `${x.length} source${x.length > 1 ? 's' : ''}: ${sysText}` : 'None', note: rec.successorOf ? 'Successor of ' + rec.successorOf : '' },
    ] },
  ];
  if (x.length) {
    sections.push({ title: 'Cross-references', kind: 'table', level: 2, meta: `${x.length} source records`, cols: ['System', 'System ID', 'Name as held there', 'Address'],
      rows: x.map((c) => ({ cells: [{ v: c.system }, { v: c.id }, { v: c.name }, { v: c.address }] })) });
  }
  if (Object.keys(rec.winners || {}).length) {
    const label = { legalName: 'Legal name', address: 'Address', taxId: 'Tax ID', paymentTerms: 'Payment terms', creditLimit: 'Credit limit' };
    const val = { legalName: rec.legalName, address: rec.address, taxId: rec.taxId ? '••-•••' + String(rec.taxId).slice(-4) : '—',
      paymentTerms: sa[0] && sa[0].paymentTerms, creditLimit: sa[0] && money(sa[0].creditLimit) };
    sections.push({ title: 'Winning values', kind: 'table', level: 2, cols: ['Attribute', 'Business ready record', 'Winning source', 'Why it won'],
      rows: Object.entries(rec.winners).map(([k, [src, pol]]) => ({ cells: [{ v: label[k] || k }, { v: val[k] || '—' }, { v: src }, cell('', pol)] })) });
  }
  sa.forEach((s) => sections.push({ title: `Extended · ${s.area}`, kind: 'kv', level: 2, rows: [
    { k: 'Payment terms', v: s.paymentTerms || '—', note: '', policy: 'BR-PT-001' }, { k: 'Credit limit', v: money(s.creditLimit), note: '', policy: 'BR-CR-001' },
    { k: 'Payment method', v: s.paymentMethod || '—', note: '', policy: 'BR-PM-001' }, { k: 'Pricing group', v: s.pricingGroup || '—', note: '', policy: 'BR-PR-001' },
    { k: 'Tax class', v: s.taxClass || '—', note: '', policy: 'BR-TX-001' }, { k: 'Controlled ordering', v: s.controlled || '—', note: '', policy: 'RG-CS-001' }] }));
  if (x.length > 1) {
    const brrVal = { name: rec.legalName, address: rec.address, taxId: rec.taxId, paymentTerms: sa[0] && sa[0].paymentTerms, creditLimit: sa[0] && sa[0].creditLimit, accountGroup: 'Sold-to' };
    const winSrc = (attr) => { const w = W(rec, attr)[0] || ''; return x.find((c) => w.includes(c.id)); };
    const attrs = [['name', 'Name', 'legalName'], ['address', 'Address', 'address'], ['taxId', 'Tax ID', 'taxId'], ['paymentTerms', 'Payment terms', 'paymentTerms'], ['creditLimit', 'Credit limit', 'creditLimit'], ['accountGroup', 'Account group', null]];
    sections.push({ title: 'Full comparison', kind: 'table', level: 3, meta: 'Highlighted cells won',
      cols: ['Attribute', 'Business ready record', ...x.map((c) => `${c.system} ${c.id}`)],
      rows: attrs.map(([f, label, wk]) => {
        const w = wk && winSrc(wk);
        const fmt = (v) => (v === null || v === undefined || v === '' ? '—' : f === 'taxId' ? '••-•••' + String(v).replace(/\D/g, '').slice(-4) : f === 'creditLimit' ? money(v) : String(v));
        return { cells: [{ v: label }, { v: fmt(brrVal[f]) }, ...x.map((c) => ({ v: fmt(c[f]), win: w && w.id === c.id, policy: w && w.id === c.id ? W(rec, wk)[1] : '' }))] };
      }) });
  }
  if ((rec.history || []).length) sections.push({ title: 'History', kind: 'table', level: 3, cols: ['When', 'Change', 'By'], rows: rec.history.map((h) => ({ cells: [{ v: h.when }, { v: h.change }, { v: h.by }] })) });
  return sections;
}

export default function Records({ arg }) {
  const list = useLoad(() => api.get('/records'), []);
  const [q, setQ] = useState('');
  const shown = (list.data || []).filter((r) => !q || `${r.id} ${r.legalName} ${r.address || ''} ${r.duns || ''} ${r.type || ''}`.toLowerCase().includes(q.toLowerCase()));
  const id = arg || (list.data && list.data[0] && list.data[0].id);
  const rec = useLoad(() => (id ? api.get('/records/' + id) : Promise.resolve(null)), [id]);
  return (
    <>
      <Title eyebrow="Business ready record · read-only" title="Business ready records">
        Search a record, open it, and use Hierarchy to see its corporate family. Key details first. Use … to open the source records behind each record, the value that won for each attribute and the policy that decided it.
      </Title>
      <Err error={list.error || rec.error} />
      <div className="row">
        <div className="side" style={{ maxWidth: 320 }}>
          <div className="stack" style={{ gap: 8 }}>
            <label className="lbl" htmlFor="rq">Search records</label>
            <input id="rq" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name, ID, DUNS, address or type" />
            <span className="small muted">{shown.length} of {(list.data || []).length} records</span>
          </div>
          <div className="stack" style={{ maxHeight: 1100, overflowY: 'auto', marginTop: 10 }}>
            {shown.map((r) => (
              <button type="button" key={r.id} className={'list-item' + (r.id === id ? ' on' : '')} onClick={() => go('records/' + r.id)}>
                <span className="mono muted">{r.id}</span><strong>{r.legalName}</strong><span className="small muted">{r.status} · {r.sources} source{r.sources === 1 ? '' : 's'}</span>
              </button>
            ))}
          </div>
        </div>
        {rec.data && (
          <div className="grow stack">
            <div className="card"><div className="row" style={{ alignItems: 'center', gap: 10 }}><span className="mono muted">{rec.data.id}</span><h2>{rec.data.legalName}</h2>
              <span className={'tag ' + (rec.data.status === 'Active' ? 'ok' : 'human')}>{rec.data.status}</span>
              <a className="btn dark" style={{ marginLeft: 'auto' }} href={'#/hierarchy/' + (rec.data.hierarchyNode ? 'brazos~' + rec.data.hierarchyNode : encodeURIComponent('record:' + rec.data.id) + '~' + rec.data.id)}>Hierarchy</a></div></div>
            <Sections sections={build(rec.data)} resetKey={rec.data.id} />
          </div>
        )}
      </div>
    </>
  );
}
