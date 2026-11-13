import React, { useState } from 'react';
import { api } from '../api.js';
import { Title, PolicyChip, useLoad, Err, AGENT_ICON } from '../components.jsx';

const GROUPS = [
  ['Orchestration', 'Orchestration', 'Runs the flow and applies the autonomy matrix', '#131820'],
  ['Core MDM', 'Master data processes', 'Build the Business ready record', '#1D47B8'],
  ['Function', 'MDM operations agents', 'Decide from documented policy', '#6D3FC0'],
  ['People support', 'Steward and lifecycle', 'Help people and watch records over time', '#0E7C66'],
];
const ICON_KEY = { Orchestrator: 'orchestrator', Intake: 'intake', 'Search before create': 'search', 'Match & merge': 'match', Enrichment: 'enrich', Validation: 'validate',
  Legal: 'legal', Procurement: 'procurement', Credit: 'credit', Tax: 'tax', 'Steward copilot': 'copilot', 'Lifecycle monitor': 'lifecycle', 'Contextual outreach': 'outreach' };

export default function Agents() {
  const a = useLoad(() => api.get('/agents'), []);
  const st = useLoad(() => api.get('/agents/stats'), []);
  const [sel, setSel] = useState('Credit');
  const [edit, setEdit] = useState(null);
  const agents = a.data || [];
  const stats = (st.data && st.data.stats) || {};
  const prov = (st.data && st.data.providers) || {};
  const cur = agents.find((x) => x.name === sel);
  const submit = async () => { await api.patch('/agents/' + encodeURIComponent(sel), edit); setEdit(null); a.reload(); };
  const auto = (n) => { const s = stats[n]; return s && s.runs ? Math.round((100 * s.auto) / s.runs) : null; };

  return (
    <>
      <Title eyebrow="Platform / Agents" title="Agents">
        {agents.length} agents. Master data processes build the record; the MDM operations agents decide from documented policy; when no policy applies, the request goes to a person.
      </Title>
      <Err error={a.error} />
      <div className="row">
        <div className="grow stack" style={{ gap: 22 }}>
          {GROUPS.map(([g, title, sub, accent]) => (
            <section key={g} className="stack" style={{ gap: 10 }}>
              <div className="row" style={{ alignItems: 'baseline', gap: 12 }}><h2>{title}</h2><span className="small muted">{sub}</span></div>
              <div className="agrid">
                {agents.filter((x) => x.group === g).map((x) => {
                  const pct = auto(x.name); const s = stats[x.name];
                  return (
                    <button type="button" key={x.name} className={'acard' + (x.name === sel ? ' on' : '')} onClick={() => { setSel(x.name); setEdit(null); }} aria-pressed={x.name === sel}>
                      <span className="stripe" style={{ background: accent }} />
                      <span className="top">
                        <span className="ic" style={{ background: accent + '14', color: accent }}>{AGENT_ICON[ICON_KEY[x.name]]}</span>
                        <span style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                          <strong style={{ fontSize: 15 }}>{x.name}</strong>
                          <span className="small" style={{ color: '#0E5A32', display: 'inline-flex', alignItems: 'center', gap: 5 }}><span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: '50%', background: '#1E8A4C' }} />Healthy · {x.version}</span>
                        </span>
                      </span>
                      <span className="small" style={{ color: 'var(--ink2)', lineHeight: '18px' }}>{x.what}</span>
                      {s && (<span className="stack" style={{ gap: 4 }}>
                        <span className="row small" style={{ justifyContent: 'space-between' }}><span className="muted">{s.runs} run{s.runs === 1 ? '' : 's'}</span><span><strong>{pct === null ? '—' : pct + '%'}</strong> on its own</span></span>
                        <span className="meter"><i style={{ width: (pct || 0) + '%' }} /></span>
                      </span>)}
                      {(prov[x.name] || []).length > 0 && <span className="row" style={{ gap: 4 }}>{prov[x.name].map((p) => <span key={p.key} className={'pmode ' + p.mode}>{p.name.split(' (')[0]} · {p.mode === 'live' ? 'Live' : 'Test data'}</span>)}</span>}
                      {x.pendingChange && <span className="small" style={{ color: 'var(--purple)' }}>Change waiting for approval</span>}
                    </button>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
        {cur && (
          <aside className="card side" aria-label="Agent settings" style={{ maxWidth: 400, position: 'sticky', top: 16 }}>
            <div className="row" style={{ alignItems: 'center', gap: 10 }}>
              <span className="ic" style={{ width: 42, height: 42, borderRadius: 12, display: 'grid', placeItems: 'center', background: '#EAF0FE', color: '#1D47B8' }}>{AGENT_ICON[ICON_KEY[cur.name]]}</span>
              <div><span className="small muted">Settings · {cur.version}</span><h2>{cur.name}</h2></div>
            </div>
            <p className="small">{cur.what}</p>
            {!edit && (<>
              <div><div className="small muted">Model</div>{cur.model}</div>
              <div><div className="small muted">Uses</div>{cur.uses}</div>
              <div><div className="small muted">Stops for a person</div>{cur.stops}</div>
              {(prov[cur.name] || []).length > 0 && <div><div className="small muted">Data providers</div><div className="row" style={{ gap: 6, marginTop: 4 }}>{prov[cur.name].map((p) => <span key={p.key} className={'pmode ' + p.mode}>{p.name} · {p.mode === 'live' ? 'Live' : 'Test data'}</span>)}</div>
                <a className="small" href="#/providers">Configure in Third-party data →</a></div>}
              {cur.policies.length > 0 && <div className="row" style={{ gap: 6 }}><span className="small muted" style={{ flexBasis: '100%' }}>Policies it runs</span>{cur.policies.map((p) => <PolicyChip key={p} id={p} />)}</div>}
              {cur.pendingChange && <div className="notice info small">Pending: {cur.pendingChange.model} · {cur.pendingChange.stops} · {cur.pendingChange.status}</div>}
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
