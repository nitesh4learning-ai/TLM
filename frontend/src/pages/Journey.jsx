import React, { useEffect, useState } from 'react';
import { api, go } from '../api.js';
import { Title, Sections, PolicyChip, useLoad, Err } from '../components.jsx';

export default function Journey({ arg }) {
  const list = useLoad(() => api.get('/requests'), []);
  const id = arg || (list.data && list.data[0] && list.data[0].id);
  const req = useLoad(() => (id ? api.get('/requests/' + id) : Promise.resolve(null)), [id]);
  const [open, setOpen] = useState(null);
  useEffect(() => setOpen(null), [id]);
  const r = req.data;
  const st = r && (r.stages.find((s) => s.key === open) || r.stages[0]);

  return (
    <>
      <Title eyebrow="Records / Request journey" title="Request journey">
        Blue stages: an agent acted on its own. Orange: a person was needed. Double-click a stage to see what it did; hover a policy ID to see the policy.
      </Title>
      <Err error={list.error || req.error} />
      <div className="row">
        <div className="side" style={{ maxWidth: 300 }}>
          <div className="stack">
            {(list.data || []).map((x) => (
              <button type="button" key={x.id} className={'list-item' + (x.id === id ? ' on' : '')} onClick={() => go('journey/' + x.id)}>
                <span className="mono muted">{x.id}</span><strong>{x.legalName}</strong><span className="small muted">{x.status}</span>
              </button>
            ))}
            {list.data && list.data.length === 0 && <p className="muted">No requests yet. Run one from <a href="#/intake">Intake</a>.</p>}
          </div>
        </div>
        {r && (
          <div className="grow stack">
            <section className="card">
              <div className="row" style={{ alignItems: 'baseline', gap: 14 }}>
                <span className="mono muted">{r.id}</span><h2>{r.legalName}</h2><span className="small muted">{r.requestType} · {r.created}</span>
                <span className={'tag ' + (r.status === 'Complete' ? 'ok' : 'human')}>{r.status}{r.touchless ? ' · touchless' : ''}</span>
                <a href={`#/records/${r.recordId}`} className="mono">{r.recordId}</a>
              </div>
              {r.llm === false && <div className="notice warn">Claude is not configured, so Intake used the sample's key values. Add ANTHROPIC_API_KEY to backend/.env for real extraction.</div>}
              <ol className="stages" aria-label="Stages">
                {r.stages.map((s, i) => (
                  <li key={s.key}>
                    <button type="button" className={`stage ${s.actor} ${s.key === st.key ? 'sel' : ''}`} aria-pressed={s.key === st.key}
                      onClick={() => setOpen(s.key)} onDoubleClick={() => setOpen(s.key)} title="Double-click for detail">
                      <span className="n">{i + 1} · {s.actor === 'human' ? 'Person' : 'Agent'}</span><span className="nm">{s.name}</span><span className="st">{s.status}</span>
                    </button>
                  </li>
                ))}
              </ol>
            </section>
            <StageDetail r={r} st={st} onChange={req.reload} />
          </div>
        )}
      </div>
    </>
  );
}

function StageDetail({ r, st, onChange }) {
  const [who, setWho] = useState(st.waitingFor || 'Data steward');
  const [note, setNote] = useState('');
  useEffect(() => setWho(st.waitingFor || 'Data steward'), [st.key]);
  const approve = async () => { await api.post(`/requests/${r.id}/stages/${st.key}/approve`, { who, note }); setNote(''); onChange(); };
  return (
    <section aria-label="Stage detail" className="stack">
      <div className="card">
        <div className="row" style={{ alignItems: 'center', gap: 10 }}>
          <h2>{st.name}</h2>
          <span className={'tag ' + st.actor}>{st.actor === 'human' ? 'A person was needed' : 'Agent acted on its own'}</span>
          {st.state === 'waiting' && <span className="tag human">Waiting for {st.waitingFor}</span>}
        </div>
        <p style={{ fontSize: 14, lineHeight: '21px' }}>{st.summary}</p>
        {st.explanation && <p className="small" style={{ lineHeight: '19px', color: 'var(--ink2)' }}><strong>Why:</strong> {st.explanation}</p>}
        <div className="row" style={{ gap: 6, alignItems: 'center' }}><span className="small muted">Policies considered</span>{st.policies.map((p) => <PolicyChip key={p} id={p} />)}</div>
        {st.state === 'waiting' && (
          <div className="row" style={{ alignItems: 'flex-end' }}>
            <div className="stack" style={{ gap: 4 }}><label className="lbl" htmlFor="who">Decided by</label><input id="who" type="text" value={who} onChange={(e) => setWho(e.target.value)} /></div>
            <div className="stack" style={{ gap: 4, flex: '1 1 240px' }}><label className="lbl" htmlFor="note">Note</label><input id="note" type="text" value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Called the owner to confirm the bank account" /></div>
            <button type="button" className="btn dark" onClick={approve}>Approve</button>
          </div>
        )}
      </div>
      <Sections sections={st.sections} resetKey={r.id + st.key} />
    </section>
  );
}
