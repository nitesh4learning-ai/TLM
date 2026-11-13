import React, { useEffect, useState } from 'react';
import { api, clearPolicyCache, setAssist } from '../api.js';
import { Title, PolicyChip, useLoad, Err } from '../components.jsx';
import PolicyForm from './PolicyForm.jsx';

const ALL = 'All agents';

export default function Policies() {
  const d = useLoad(() => api.get('/policies'), []);
  const [folder, setFolder] = useState('all');
  const [agentF, setAgentF] = useState('');
  const [q, setQ] = useState('');
  const [sel, setSel] = useState(null);
  const [editing, setEditing] = useState(false);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const pols = (d.data && d.data.policies) || [];
  const list = pols.filter((p) => (folder === 'all' || p.folder === folder)
    && (!agentF || (p.appliesTo || []).includes(agentF) || (p.appliesTo || []).includes(ALL))
    && (!q || `${p.id} ${p.title} ${p.text} ${(p.appliesTo || []).join(' ')}`.toLowerCase().includes(q.toLowerCase())));
  const cur = pols.find((p) => p.id === sel) || list[0];
  useEffect(() => setEditing(false), [sel]);
  useEffect(() => { if (cur) setAssist({ page: 'Master data policies', policyId: cur.id, label: `${cur.id} · ${cur.title}` }); }, [cur && cur.id]); // eslint-disable-line

  const upload = async (e) => {
    const f = e.target.files[0]; if (!f) return;
    setBusy(true); setMsg(null);
    try { const p = await api.upload('/policies/upload', [f], 'file'); clearPolicyCache(); d.reload(); setSel(p.id); setFolder('all'); setEditing(true); setMsg({ ok: true, t: `Filled ${p.id} "${p.title}" from ${f.name}: ${p.completeness.score}% complete. Fields marked “Needs governance input” were not in the document.` }); }
    catch (err) { setMsg({ ok: false, t: err.message }); } finally { setBusy(false); e.target.value = ''; }
  };
  const setLevel = async (p, l) => {
    if (p.level === l) return;
    const saved = await api.put('/policies/' + p.id, { level: l }); clearPolicyCache(); d.reload();
    setMsg({ ok: true, t: `${saved.id} is now autonomy ${l} (version ${saved.version}).` });
  };
  const create = async () => { const p = await api.post('/policies', { title: 'New policy', appliesTo: ['Orchestrator'], status: 'Draft' }); clearPolicyCache(); d.reload(); setSel(p.id); setFolder('all'); setEditing(true); };

  return (
    <>
      <Title eyebrow="Master data policies" title="Policies" right={<div className="row" style={{ gap: 8 }}>
        <label className="btn" style={{ position: 'relative' }}>{busy ? 'Drafting…' : 'Upload policy document'}<input type="file" accept=".pdf,.docx,.md,.txt" onChange={upload} style={{ position: 'absolute', opacity: 0, width: 1, height: 1 }} /></label>
        <button type="button" className="btn dark" onClick={create}>New policy</button></div>}>
        Every policy uses one form. Upload a policy document and Claude fills in what the document says; anything it does not say is marked for governance to fill in. Business-rule policies run through one rules engine for all agents.
      </Title>
      <Err error={d.error} />
      {msg && <div className={'notice ' + (msg.ok ? 'info' : 'err')} role="status">{msg.t}</div>}
      <div className="row">
        <nav className="card side" aria-label="Policy folders" style={{ maxWidth: 260 }}>
          <label className="lbl" htmlFor="ps">Search policies</label>
          <input id="ps" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="ID, title, agent or text" />
          <label className="lbl" htmlFor="pa">Agent</label>
          <select id="pa" value={agentF} onChange={(e) => setAgentF(e.target.value)}><option value="">Any agent</option>{((d.data && d.data.agents) || []).filter((a) => a !== ALL).map((a) => <option key={a}>{a}</option>)}</select>
          {[{ key: 'all', name: 'All policies' }, ...((d.data && d.data.folders) || [])].map((f) => (
            <button type="button" key={f.key} className={'list-item' + (folder === f.key ? ' on' : '')} style={{ flexDirection: 'row', justifyContent: 'space-between' }} onClick={() => { setFolder(f.key); setSel(null); }}>
              <span>{f.name}</span><span className="small muted">{f.key === 'all' ? pols.length : pols.filter((p) => p.folder === f.key).length}</span>
            </button>
          ))}
        </nav>
        <div className="side stack" style={{ maxWidth: 300, gap: 8 }}>
          {list.length === 0 && <p className="card muted small">No policy matches. A request with no matching policy goes to a person (AG-001).</p>}
          {list.map((p) => (
            <button type="button" key={p.id} className={'list-item' + (cur && p.id === cur.id ? ' on' : '')} onClick={() => setSel(p.id)}>
              <span className="row" style={{ gap: 8, alignItems: 'center' }}><span className="mono muted">{p.id} · v{p.version}</span><span className={'lvl ' + p.level}>{p.level}</span>
                {p.status !== 'Active' && <span className="small" style={{ color: 'var(--purple)' }}>{p.status}</span>}</span>
              <strong>{p.title}</strong><span className="small muted">{(p.appliesTo || []).join(', ')}</span>
            </button>
          ))}
        </div>
        {cur && editing && d.data && <PolicyForm key={cur.id + cur.version} p={cur} meta={d.data} onSaved={(s) => { setEditing(false); d.reload(); setMsg({ ok: true, t: `${s.id} saved as version ${s.version}. Agents use it from the next request.` }); }} onCancel={() => setEditing(false)} />}
        {cur && !editing && (
          <article className="card grow">
            <div className="row" style={{ alignItems: 'center', gap: 10 }}><span className="mono muted">{cur.id}</span><h2>{cur.title}</h2><span className={'lvl ' + cur.level}>{cur.level} · {cur.levelName}</span>
              <button type="button" className="btn dark" style={{ marginLeft: 'auto' }} onClick={() => setEditing(true)}>Edit policy</button></div>
            <div className="row small muted" style={{ gap: 18 }}><span>Folder: {cur.folderName}</span><span>Stage: {cur.stage}</span><span>Owner: {cur.owner}</span><span>Effective {cur.effective}</span><span>{cur.status} · v{cur.version}</span></div>
            {cur.status === 'Draft' && <div className="notice warn small">Draft: agents do not read this policy until it is complete and activated. Fields marked “Needs governance input” were not in the uploaded document.</div>}
            <div className="row" style={{ gap: 6, alignItems: 'center' }}><span className="small muted">Applies to</span>{(cur.appliesTo || []).map((a) => <span key={a} className={'pmode ' + (a === ALL ? 'live' : 'test')} style={a === ALL ? {} : { background: '#EAF0FE', color: '#1D47B8', borderColor: '#9DB3EE' }}>{a}</span>)}
              {(cur.roles || []).map((r) => <span key={r} className="pmode" style={{ background: '#FFF1DE', color: '#7A3B00', border: '1px solid #F2B872' }}>{r}</span>)}</div>
            <h3>In plain English</h3><p style={{ fontSize: 14, lineHeight: '22px' }}>{cur.text}</p>
            {(cur.params || []).length > 0 && (<>
              <h3>Values the agents run</h3>
              <div className="scroll"><table><thead><tr><th>Name</th><th>Value</th><th>What it controls</th></tr></thead>
                <tbody>{cur.params.map((x) => <tr key={x.key}><td className="mono">{x.key}</td><td><strong>{String(x.value)}</strong></td><td>{x.help}</td></tr>)}</tbody></table></div>
            </>)}
            {(cur.rules || []).length > 0 && (<>
              <h3>Rules the agents run</h3>
              <div className="scroll"><table><thead><tr><th>#</th><th>When</th><th>Then</th><th>Decided by</th></tr></thead>
                <tbody>{cur.rules.map((r, i) => <tr key={i}><td>{i + 1}</td><td className="small">{(r.when || []).length ? r.when.map((c) => `${c.attr} ${c.op}${['exists', 'not exists'].includes(c.op) ? '' : ' ' + c.value}`).join(' and ') : 'Otherwise'}</td>
                  <td className="small">{Object.entries(r.then || {}).map(([k, v]) => `${k} = ${v}`).join(', ')}{r.note ? <span className="muted"> · {r.note}</span> : null}</td>
                  <td><span className={'tag ' + (r.decidedBy === 'Agent' ? 'agent' : 'human')}>{r.decidedBy}</span></td></tr>)}</tbody></table></div>
            </>)}
            {(cur.survivorship || []).length > 0 && (<>
              <h3>Survivorship rules (run by the Match &amp; merge agent)</h3>
              <div className="scroll"><table><thead><tr><th>Attribute</th><th>Method</th><th>Source order</th></tr></thead>
                <tbody>{cur.survivorship.map((r) => <tr key={r.attribute}><td className="mono">{r.attribute}</td><td>{r.method}</td><td className="small">{(r.order || []).join(' › ')}</td></tr>)}</tbody></table></div>
            </>)}
            {(cur.inputs || []).length > 0 && <div className="row" style={{ gap: 6, alignItems: 'center' }}><span className="small muted">Reads</span>{cur.inputs.map((x) => <span key={x.attribute} className="chip2" style={{ cursor: 'default' }}>{x.attribute} · {x.source}</span>)}</div>}
            <div className="row small muted" style={{ gap: 18 }}><span>Approver: {cur.approverRole || '—'}</span><span>Response time: {cur.slaHours ? cur.slaHours + ' h' : '—'}</span><span>Priority {cur.priority}{cur.complianceFloor ? ' · compliance floor' : ''}</span><span>Record types: {(cur.recordTypes || []).join(', ')}</span><span>Runs on: {(cur.triggers || []).join(', ')}</span></div>
            {cur.completeness && cur.completeness.score < 100 && <div className="notice warn small">Form {cur.completeness.score}% complete. Missing: {cur.completeness.missing.join(', ')}.</div>}
            <h3>Conditions and actions (as written)</h3>
            <div className="scroll"><table><thead><tr><th>Condition</th><th>Action</th><th>Decided by</th></tr></thead>
              <tbody>{(cur.rows || []).map((r, i) => <tr key={i}><td>{r[0]}</td><td>{r[1]}</td><td><span className={'tag ' + (r[2] === 'Agent' ? 'agent' : 'human')}>{r[2]}</span></td></tr>)}</tbody></table></div>
            <p className="small"><strong>Exceptions.</strong> {cur.exceptions}</p>
            {(cur.cites || []).length > 0 && <div className="row" style={{ gap: 6, alignItems: 'center' }}><span className="small muted">Related</span>{cur.cites.map((c) => <PolicyChip key={c} id={c} />)}</div>}
            {cur.source && <p className="small muted">Source: {String(cur.source).startsWith('http') ? <a href={cur.source}>{cur.source}</a> : cur.source}</p>}
            <h3>Version history</h3>
            <ol className="trail">{(cur.history || []).map((h) => <li key={h.version}><strong>v{h.version}</strong> · {h.at} · {h.by} · {h.changes}</li>)}</ol>
          </article>
        )}
      </div>
      <section className="card">
        <h2>Autonomy matrix</h2>
        <p className="small muted">Click a cell to change who decides for that policy. Each change publishes a new version; agents use it from the next request.</p>
        <div className="scroll"><table><thead><tr><th>Policy</th><th>Applies to</th><th style={{ textAlign: 'center' }}>A · Agent decides</th><th style={{ textAlign: 'center' }}>B · Person approves above limit</th><th style={{ textAlign: 'center' }}>H · Person decides</th></tr></thead>
          <tbody>{pols.filter((p) => p.status === 'Active').map((p) => <tr key={p.id}><td><PolicyChip id={p.id} /> {p.title}</td><td className="small">{(p.appliesTo || []).join(', ')}</td>{['A', 'B', 'H'].map((l) => <td key={l} style={{ textAlign: 'center', padding: 4 }}>
            <button type="button" className={'mcell' + (p.level === l ? ' on ' + l : '')} aria-pressed={p.level === l} aria-label={`${p.id}: set autonomy ${l}`} onClick={() => setLevel(p, l)}>{p.level === l ? '●' : ''}</button></td>)}</tr>)}</tbody></table></div>
      </section>
    </>
  );
}
