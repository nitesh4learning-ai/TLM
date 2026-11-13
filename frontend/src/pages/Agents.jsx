import React, { useState } from 'react';
import { api } from '../api.js';
import { Title, PolicyChip, useLoad, Err } from '../components.jsx';

const GROUPS = [['Orchestration', 'Runs the flow'], ['Core MDM', 'Build the Business ready record'], ['Function', 'Decide from documented policy'], ['People support', 'Help people and watch records over time']];

export default function Agents() {
  const a = useLoad(() => api.get('/agents'), []);
  const [sel, setSel] = useState('Credit');
  const [edit, setEdit] = useState(null);
  const agents = a.data || [];
  const cur = agents.find((x) => x.name === sel);
  const submit = async () => { await api.patch('/agents/' + encodeURIComponent(sel), edit); setEdit(null); a.reload(); };
  return (
    <>
      <Title eyebrow="Platform / Agents" title="Agents">
        {agents.length} agents. Core MDM agents build the record; Legal, Procurement, Credit and Tax decide from documented policy. When no policy applies, the request goes to a person.
      </Title>
      <Err error={a.error} />
      <div className="row">
        <div className="grow stack">
          {GROUPS.map(([g, sub]) => (
            <section key={g} className="stack" style={{ gap: 8 }}>
              <div className="row" style={{ alignItems: 'baseline', gap: 12 }}><h2>{g === 'Function' ? 'Function agents' : g === 'Core MDM' ? 'Core MDM agents' : g === 'People support' ? 'Steward and lifecycle' : g}</h2><span className="small muted">{sub}</span></div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
                {agents.filter((x) => x.group === g).map((x) => (
                  <button type="button" key={x.name} className={'list-item' + (x.name === sel ? ' on' : '')} onClick={() => { setSel(x.name); setEdit(null); }}>
                    <strong>{x.name}</strong><span className="small muted">{x.what}</span>{x.pendingChange && <span className="small" style={{ color: 'var(--purple)' }}>Change waiting for approval</span>}
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>
        {cur && (
          <aside className="card side" aria-label="Agent settings" style={{ maxWidth: 400 }}>
            <span className="small muted">Settings · {cur.version}</span><h2>{cur.name}</h2><p className="small">{cur.what}</p>
            {!edit && (<>
              <div><div className="small muted">Model</div>{cur.model}</div>
              <div><div className="small muted">Uses</div>{cur.uses}</div>
              <div><div className="small muted">Stops for a person</div>{cur.stops}</div>
              {cur.policies.length > 0 && <div className="row" style={{ gap: 6 }}><span className="small muted" style={{ flexBasis: '100%' }}>Policies it runs</span>{cur.policies.map((p) => <PolicyChip key={p} id={p} />)}</div>}
              {cur.pendingChange && <div className="notice info small">Pending: {cur.pendingChange.model} · {cur.pendingChange.stops} — {cur.pendingChange.status}</div>}
              <button type="button" className="btn" style={{ alignSelf: 'flex-start' }} onClick={() => setEdit({ model: cur.model, stops: cur.stops })}>Edit settings</button>
            </>)}
            {edit && (<>
              <label className="lbl" htmlFor="m">Model</label><input id="m" type="text" value={edit.model} onChange={(e) => setEdit({ ...edit, model: e.target.value })} />
              <label className="lbl" htmlFor="s">Stops for a person (guardrail)</label><textarea id="s" rows={3} value={edit.stops} onChange={(e) => setEdit({ ...edit, stops: e.target.value })} />
              <p className="small muted">Changes take effect after governance approval (AG-001). Thresholds live in the policy store.</p>
              <div className="row" style={{ gap: 8 }}><button type="button" className="btn dark" onClick={submit}>Submit for approval</button><button type="button" className="btn" onClick={() => setEdit(null)}>Cancel</button></div>
            </>)}
          </aside>
        )}
      </div>
    </>
  );
}
