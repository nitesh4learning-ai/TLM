import React from 'react';
import { api } from '../api.js';
import { Title, useLoad, Err } from '../components.jsx';

export default function ControlTower() {
  const s = useLoad(() => api.get('/summary'), []);
  const r = useLoad(() => api.get('/requests'), []);
  const d = s.data || {};
  const reset = async () => { if (window.confirm('Clear all requests and reset records to the starting data?')) { await api.post('/reset'); s.reload(); r.reload(); } };
  return (
    <>
      <Title eyebrow="Overview" title="Control tower" right={<button type="button" className="btn" onClick={reset}>Reset data</button>}>
        Requests flow through the core MDM agents, then Legal, Procurement, Credit and Tax. Start one from Intake.
      </Title>
      <Err error={s.error} />
      <div className="kpis">
        <div className="kpi"><div className="small muted">Requests</div><div className="val">{d.requests ?? '—'}</div></div>
        <div className="kpi"><div className="small muted">Touchless</div><div className="val">{d.requests ? `${Math.round((100 * d.touchless) / d.requests)}%` : '—'}</div></div>
        <div className="kpi"><div className="small muted">Waiting on a person</div><div className="val">{d.waiting ?? '—'}</div></div>
        <div className="kpi"><div className="small muted">Business ready records</div><div className="val">{d.records ?? '—'}</div></div>
        <div className="kpi"><div className="small muted">Policies · agents</div><div className="val">{d.policies ?? '—'} · {d.agents ?? '—'}</div></div>
      </div>
      <section className="card">
        <h2>Recent requests</h2>
        {r.data && r.data.length === 0 && <p className="muted">No requests yet. Go to <a href="#/intake">Intake</a> to run one.</p>}
        {r.data && r.data.length > 0 && (
          <div className="scroll"><table><thead><tr><th>Request</th><th>Party</th><th>Type</th><th>Record</th><th>Status</th></tr></thead>
            <tbody>{r.data.map((x) => (
              <tr key={x.id}><td><a href={`#/journey/${x.id}`} className="mono">{x.id}</a></td><td>{x.legalName}</td><td>{x.requestType}</td>
                <td><a href={`#/records/${x.recordId}`} className="mono">{x.recordId}</a></td>
                <td><span className={'tag ' + (x.status === 'Complete' ? (x.touchless ? 'agent' : 'ok') : 'human')}>{x.status === 'Complete' && x.touchless ? 'Complete · touchless' : x.status}</span></td></tr>
            ))}</tbody></table></div>
        )}
      </section>
    </>
  );
}
