import React, { useEffect, useState } from 'react';
import { api, clearPolicyCache } from '../api.js';
import { Title, PolicyChip, useLoad, Err } from '../components.jsx';

const ALL = 'All agents';

function Edit({ p, meta, onSaved, onCancel }) {
  const [f, setF] = useState(() => JSON.parse(JSON.stringify(p)));
  const [err, setErr] = useState(null);
  const [roleText, setRoleText] = useState((p.roles || []).join(', '));
  const set = (k, v) => setF({ ...f, [k]: v });
  const toggleAgent = (a) => {
    let cur = f.appliesTo || [];
    if (a === ALL) cur = cur.includes(ALL) ? [] : [ALL];
    else cur = cur.includes(a) ? cur.filter((x) => x !== a) : [...cur.filter((x) => x !== ALL), a];
    set('appliesTo', cur);
  };
  const save = async () => {
    setErr(null);
    const body = { title: f.title, folder: f.folder, stage: f.stage, level: f.level, owner: f.owner, text: f.text, exceptions: f.exceptions,
      rows: f.rows, appliesTo: f.appliesTo, roles: roleText.split(',').map((x) => x.trim()).filter(Boolean), params: f.params, effective: f.effective,
      status: f.status === 'Draft' ? 'Active' : f.status };
    try { const saved = await api.put('/policies/' + p.id, body); clearPolicyCache(); onSaved(saved); } catch (e) { setErr(e.message); }
  };
  const row = (i, j, v) => { const rows = f.rows.map((r) => [...r]); rows[i][j] = v; set('rows', rows); };
  const param = (i, k, v) => { const ps = f.params.map((x) => ({ ...x })); ps[i][k] = v; set('params', ps); };
  return (
    <article className="card grow" aria-label={'Edit ' + p.id}>
      <div className="row" style={{ alignItems: 'center', gap: 10 }}><span className="mono muted">{p.id}</span><h2>Edit policy</h2><span className="small muted">Saving publishes version {p.version + 1}. Agents use it from the next request.</span></div>
      <Err error={err} />
      <div className="form">
        <div className="f" style={{ gridColumn: '1 / -1' }}><label className="lbl" htmlFor="e-t">Title</label><input id="e-t" type="text" value={f.title} onChange={(e) => set('title', e.target.value)} /></div>
        <div className="f"><label className="lbl" htmlFor="e-f">Folder</label><select id="e-f" value={f.folder} onChange={(e) => set('folder', e.target.value)}>{meta.folders.map((x) => <option key={x.key} value={x.key}>{x.name}</option>)}</select></div>
        <div className="f"><label className="lbl" htmlFor="e-l">Autonomy</label><select id="e-l" value={f.level} onChange={(e) => set('level', e.target.value)}>{Object.entries(meta.levels).map(([k, v]) => <option key={k} value={k}>{k} · {v}</option>)}</select></div>
        <div className="f"><label className="lbl" htmlFor="e-o">Owner</label><input id="e-o" type="text" value={f.owner} onChange={(e) => set('owner', e.target.value)} /></div>
        <div className="f"><label className="lbl" htmlFor="e-d">Effective date</label><input id="e-d" type="text" value={f.effective || ''} onChange={(e) => set('effective', e.target.value)} placeholder="YYYY-MM-DD" /></div>
        <div className="f"><label className="lbl" htmlFor="e-s">Stage</label><input id="e-s" type="text" value={f.stage} onChange={(e) => set('stage', e.target.value)} /></div>
        <div className="f"><label className="lbl" htmlFor="e-st">Status</label><select id="e-st" value={f.status === 'Draft' ? 'Active' : f.status} onChange={(e) => set('status', e.target.value)}><option>Active</option><option>Retired</option></select></div>
      </div>
      <fieldset style={{ border: '1px solid var(--line)', borderRadius: 12, padding: 12 }}>
        <legend className="small" style={{ fontWeight: 600, padding: '0 6px' }}>Applies to agents</legend>
        <div className="row" style={{ gap: 8 }}>
          {meta.agents.map((a) => (
            <label key={a} className={'agentpick' + ((f.appliesTo || []).includes(a) ? ' on' : '')}>
              <input type="checkbox" checked={(f.appliesTo || []).includes(a)} onChange={() => toggleAgent(a)} />{a}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="f"><label className="lbl" htmlFor="e-r">Applies to people (roles, comma-separated)</label><input id="e-r" type="text" value={roleText} onChange={(e) => setRoleText(e.target.value)} placeholder="e.g. Credit manager, BU finance director" /></div>
      <div className="f"><label className="lbl" htmlFor="e-x">In plain English</label><textarea id="e-x" rows={4} value={f.text} onChange={(e) => set('text', e.target.value)} /></div>
      <h3>Values the agents run</h3>
      {(f.params || []).length === 0 && <p className="small muted">This policy has no numeric values; agents apply its conditions as written.</p>}
      <div className="stack" style={{ gap: 8 }}>
        {(f.params || []).map((x, i) => (
          <div key={i} className="row" style={{ alignItems: 'flex-end', gap: 8 }}>
            <div className="f" style={{ flex: '1 1 200px' }}><label className="lbl" htmlFor={'pk' + i}>Name</label><input id={'pk' + i} type="text" value={x.key} onChange={(e) => param(i, 'key', e.target.value)} /></div>
            <div className="f" style={{ flex: '0 1 160px' }}><label className="lbl" htmlFor={'pv' + i}>Value</label><input id={'pv' + i} type="text" value={x.value} onChange={(e) => param(i, 'value', e.target.value)} /></div>
            <div className="f" style={{ flex: '2 1 260px' }}><label className="lbl" htmlFor={'ph' + i}>What it controls</label><input id={'ph' + i} type="text" value={x.help || ''} onChange={(e) => param(i, 'help', e.target.value)} /></div>
            <button type="button" className="btn" onClick={() => set('params', f.params.filter((_, j) => j !== i))} aria-label="Remove value">Remove</button>
          </div>
        ))}
        <button type="button" className="btn" style={{ alignSelf: 'flex-start' }} onClick={() => set('params', [...(f.params || []), { key: '', value: '', help: '' }])}>Add value</button>
      </div>
      <h3>Conditions and actions</h3>
      <div className="stack" style={{ gap: 8 }}>
        {(f.rows || []).map((r, i) => (
          <div key={i} className="row" style={{ alignItems: 'flex-end', gap: 8 }}>
            <div className="f" style={{ flex: '2 1 240px' }}><label className="lbl" htmlFor={'rc' + i}>Condition</label><input id={'rc' + i} type="text" value={r[0]} onChange={(e) => row(i, 0, e.target.value)} /></div>
            <div className="f" style={{ flex: '2 1 240px' }}><label className="lbl" htmlFor={'ra' + i}>Action</label><input id={'ra' + i} type="text" value={r[1]} onChange={(e) => row(i, 1, e.target.value)} /></div>
            <div className="f" style={{ flex: '1 1 160px' }}><label className="lbl" htmlFor={'rd' + i}>Decided by</label><input id={'rd' + i} type="text" value={r[2]} onChange={(e) => row(i, 2, e.target.value)} /></div>
            <button type="button" className="btn" onClick={() => set('rows', f.rows.filter((_, j) => j !== i))} aria-label="Remove condition">Remove</button>
          </div>
        ))}
        <button type="button" className="btn" style={{ alignSelf: 'flex-start' }} onClick={() => set('rows', [...(f.rows || []), ['', '', 'Agent']])}>Add condition</button>
      </div>
      <div className="f"><label className="lbl" htmlFor="e-ex">Exceptions</label><textarea id="e-ex" rows={2} value={f.exceptions} onChange={(e) => set('exceptions', e.target.value)} /></div>
      <div className="row" style={{ gap: 8 }}><button type="button" className="btn dark" onClick={save}>Save and publish</button><button type="button" className="btn" onClick={onCancel}>Cancel</button></div>
    </article>
  );
}

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

  const upload = async (e) => {
    const f = e.target.files[0]; if (!f) return;
    setBusy(true); setMsg(null);
    try { const p = await api.upload('/policies/upload', [f], 'file'); clearPolicyCache(); d.reload(); setSel(p.id); setFolder('all'); setEditing(true); setMsg({ ok: true, t: `Drafted ${p.id} "${p.title}" from ${f.name}. Review it, then save to publish.` }); }
    catch (err) { setMsg({ ok: false, t: err.message }); } finally { setBusy(false); e.target.value = ''; }
  };
  const setLevel = async (p, l) => {
    if (p.level === l) return;
    const saved = await api.put('/policies/' + p.id, { level: l }); clearPolicyCache(); d.reload();
    setMsg({ ok: true, t: `${saved.id} is now autonomy ${l} (version ${saved.version}).` });
  };
  const create = async () => { const p = await api.post('/policies', { title: 'New policy', appliesTo: ['Orchestrator'] }); clearPolicyCache(); d.reload(); setSel(p.id); setFolder('all'); setEditing(true); };

  return (
    <>
      <Title eyebrow="Master data policies" title="Policies" right={<div className="row" style={{ gap: 8 }}>
        <label className="btn" style={{ position: 'relative' }}>{busy ? 'Drafting…' : 'Upload policy document'}<input type="file" accept=".pdf,.docx,.md,.txt" onChange={upload} style={{ position: 'absolute', opacity: 0, width: 1, height: 1 }} /></label>
        <button type="button" className="btn dark" onClick={create}>New policy</button></div>}>
        Edit any policy and assign it to the agents that should read it, or to all agents. Saving publishes a new version straight away; the next request uses it, and every decision records the version it used.
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
        {cur && editing && d.data && <Edit key={cur.id + cur.version} p={cur} meta={d.data} onSaved={(s) => { setEditing(false); d.reload(); setMsg({ ok: true, t: `${s.id} saved as version ${s.version}. Agents use it from the next request.` }); }} onCancel={() => setEditing(false)} />}
        {cur && !editing && (
          <article className="card grow">
            <div className="row" style={{ alignItems: 'center', gap: 10 }}><span className="mono muted">{cur.id}</span><h2>{cur.title}</h2><span className={'lvl ' + cur.level}>{cur.level} · {cur.levelName}</span>
              <button type="button" className="btn dark" style={{ marginLeft: 'auto' }} onClick={() => setEditing(true)}>Edit policy</button></div>
            <div className="row small muted" style={{ gap: 18 }}><span>Folder: {cur.folderName}</span><span>Stage: {cur.stage}</span><span>Owner: {cur.owner}</span><span>Effective {cur.effective}</span><span>{cur.status} · v{cur.version}</span></div>
            {cur.status === 'Draft' && <div className="notice warn small">Draft: agents do not read this policy until you review and save it.</div>}
            <div className="row" style={{ gap: 6, alignItems: 'center' }}><span className="small muted">Applies to</span>{(cur.appliesTo || []).map((a) => <span key={a} className={'pmode ' + (a === ALL ? 'live' : 'test')} style={a === ALL ? {} : { background: '#EAF0FE', color: '#1D47B8', borderColor: '#9DB3EE' }}>{a}</span>)}
              {(cur.roles || []).map((r) => <span key={r} className="pmode" style={{ background: '#FFF1DE', color: '#7A3B00', border: '1px solid #F2B872' }}>{r}</span>)}</div>
            <h3>In plain English</h3><p style={{ fontSize: 14, lineHeight: '22px' }}>{cur.text}</p>
            {(cur.params || []).length > 0 && (<>
              <h3>Values the agents run</h3>
              <div className="scroll"><table><thead><tr><th>Name</th><th>Value</th><th>What it controls</th></tr></thead>
                <tbody>{cur.params.map((x) => <tr key={x.key}><td className="mono">{x.key}</td><td><strong>{String(x.value)}</strong></td><td>{x.help}</td></tr>)}</tbody></table></div>
            </>)}
            <h3>Conditions and actions</h3>
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
