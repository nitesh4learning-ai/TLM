import React, { useState } from 'react';
import { api, clearPolicyCache } from '../api.js';
import { Title, PolicyChip, useLoad, Err } from '../components.jsx';

export default function Policies() {
  const d = useLoad(() => api.get('/policies'), []);
  const [folder, setFolder] = useState('all');
  const [q, setQ] = useState('');
  const [sel, setSel] = useState(null);
  const [draft, setDraft] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const pols = (d.data && d.data.policies) || [];
  const list = pols.filter((p) => (folder === 'all' || p.folder === folder) && (!q || `${p.id} ${p.title} ${p.text} ${p.agent}`.toLowerCase().includes(q.toLowerCase())));
  const cur = pols.find((p) => p.id === sel) || list[0];

  const save = async () => { await api.put('/policies/' + cur.id, { text: draft }); clearPolicyCache(); setDraft(null); d.reload(); };
  const upload = async (e) => {
    const f = e.target.files[0]; if (!f) return;
    setBusy(true); setMsg(null);
    try { const p = await api.upload('/policies/upload', [f], 'file'); clearPolicyCache(); d.reload(); setSel(p.id); setFolder('all'); setMsg({ ok: true, t: `Drafted ${p.id} "${p.title}" from ${f.name}. Review it before publishing.` }); }
    catch (err) { setMsg({ ok: false, t: err.message }); } finally { setBusy(false); e.target.value = ''; }
  };

  return (
    <>
      <Title eyebrow="Platform / Policy studio" title="Policy studio" right={
        <label className="btn" style={{ position: 'relative' }}>{busy ? 'Drafting…' : 'Upload policy document'}
          <input type="file" accept=".pdf,.docx,.md,.txt" onChange={upload} style={{ position: 'absolute', opacity: 0, width: 1, height: 1 }} /></label>}>
        Every policy has one autonomy level: the agent decides (A), the agent decides and a person approves above a limit (B), or a person decides (H). When no policy applies, the request goes to a person.
      </Title>
      <Err error={d.error} />
      {msg && <div className={'notice ' + (msg.ok ? 'info' : 'err')} role="status">{msg.t}</div>}
      <div className="row">
        <nav className="card side" aria-label="Policy folders" style={{ maxWidth: 260 }}>
          <label className="lbl" htmlFor="ps">Search policies</label>
          <input id="ps" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="ID, title, agent or text" />
          {[{ key: 'all', name: 'All policies' }, ...((d.data && d.data.folders) || [])].map((f) => (
            <button type="button" key={f.key} className={'list-item' + (folder === f.key ? ' on' : '')} style={{ flexDirection: 'row', justifyContent: 'space-between' }} onClick={() => { setFolder(f.key); setSel(null); }}>
              <span>{f.name}</span><span className="small muted">{f.key === 'all' ? pols.length : pols.filter((p) => p.folder === f.key).length}</span>
            </button>
          ))}
        </nav>
        <div className="side stack" style={{ maxWidth: 300, gap: 8 }}>
          {list.length === 0 && <p className="card muted small">No policy matches. A request with no matching policy goes to a person (AG-001).</p>}
          {list.map((p) => (
            <button type="button" key={p.id} className={'list-item' + (cur && p.id === cur.id ? ' on' : '')} onClick={() => { setSel(p.id); setDraft(null); }}>
              <span className="row" style={{ gap: 8, alignItems: 'center' }}><span className="mono muted">{p.id}</span><span className={'lvl ' + p.level}>{p.level}</span>{p.status === 'Draft' && <span className="small" style={{ color: 'var(--purple)' }}>Draft</span>}</span>
              <strong>{p.title}</strong><span className="small muted">Agent: {p.agent}</span>
            </button>
          ))}
        </div>
        {cur && (
          <article className="card grow">
            <div className="row" style={{ alignItems: 'center', gap: 10 }}><span className="mono muted">{cur.id}</span><h2>{cur.title}</h2><span className={'lvl ' + cur.level}>{cur.level} · {cur.levelName}</span></div>
            <div className="row small muted" style={{ gap: 18 }}><span>Folder: {cur.folderName}</span><span>Stage: {cur.stage}</span><span>Agent: {cur.agent}</span><span>Owner: {cur.owner}</span><span>{cur.status} v{cur.version}</span></div>
            <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}><h3>In plain English</h3>{draft === null && <button type="button" className="btn" onClick={() => setDraft(cur.text)}>Edit policy</button>}</div>
            {draft === null ? <p style={{ fontSize: 14, lineHeight: '22px' }}>{cur.text}</p> : (<>
              <label className="lbl" htmlFor="pe">Policy text</label><textarea id="pe" rows={5} value={draft} onChange={(e) => setDraft(e.target.value)} />
              <div className="row" style={{ gap: 8 }}><button type="button" className="btn dark" onClick={save}>Save draft</button><button type="button" className="btn" onClick={() => setDraft(null)}>Cancel</button></div>
            </>)}
            {cur.status === 'Draft' && <p className="small" style={{ color: 'var(--purple)' }}>Draft saved. Needs a second governance reviewer before it is published.</p>}
            <h3>Conditions and actions</h3>
            <div className="scroll"><table><thead><tr><th>Condition</th><th>Action</th><th>Decided by</th></tr></thead>
              <tbody>{(cur.rows || []).map((r, i) => <tr key={i}><td>{r[0]}</td><td>{r[1]}</td><td><span className={'tag ' + (r[2] === 'Agent' ? 'agent' : 'human')}>{r[2]}</span></td></tr>)}</tbody></table></div>
            <p className="small"><strong>Exceptions.</strong> {cur.exceptions}</p>
            {(cur.cites || []).length > 0 && <div className="row" style={{ gap: 6, alignItems: 'center' }}><span className="small muted">Related</span>{cur.cites.map((c) => <PolicyChip key={c} id={c} />)}</div>}
            {cur.source && <p className="small muted">Source: {cur.source.startsWith('http') ? <a href={cur.source}>{cur.source}</a> : cur.source}</p>}
          </article>
        )}
      </div>
      <section className="card">
        <h2>Autonomy matrix</h2>
        <div className="scroll"><table><thead><tr><th>Policy</th><th>Agent</th><th style={{ textAlign: 'center' }}>A · Agent decides</th><th style={{ textAlign: 'center' }}>B · Person approves above limit</th><th style={{ textAlign: 'center' }}>H · Person decides</th></tr></thead>
          <tbody>{pols.map((p) => <tr key={p.id}><td><PolicyChip id={p.id} /> {p.title}</td><td>{p.agent}</td>{['A', 'B', 'H'].map((l) => <td key={l} style={{ textAlign: 'center' }}>{p.level === l ? '●' : ''}</td>)}</tr>)}</tbody></table></div>
      </section>
    </>
  );
}
