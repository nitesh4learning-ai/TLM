import React, { useEffect, useRef, useState } from 'react';
import { api, go } from '../api.js';
import { Title, Sections, PolicyChip, useLoad, Err, EmailPreview, AGENT_ICON } from '../components.jsx';

const GROUPS = [
  { key: 'intake', title: 'Intake', sub: 'Read the request', stages: ['intake'] },
  { key: 'core', title: 'Master data processes', sub: 'Build the record', stages: ['search', 'match', 'enrich', 'validate'] },
  { key: 'ops', title: 'MDM operations agents', sub: 'Decide from policy', stages: ['legal', 'procurement', 'credit', 'tax'] },
  { key: 'record', title: 'Business ready record', sub: 'Publish', stages: ['record'] },
];

function stateOf(s, idx, shown, running) {
  if (idx >= shown) return idx === shown && running ? 'running' : 'pending';
  return s.state === 'waiting' ? 'waiting' : s.state === 'approved' ? 'approved' : 'done';
}
const STATE_LABEL = { done: 'Done', waiting: 'Waiting for a person', approved: 'Approved', pending: 'Not started', running: 'Working' };

export default function Journey({ arg }) {
  const [rid, flag] = (arg || '').split('~');
  const list = useLoad(() => api.get('/requests'), []);
  const settings = useLoad(() => api.get('/providers'), []);
  const id = rid || (list.data && list.data[0] && list.data[0].id);
  const req = useLoad(() => (id ? api.get('/requests/' + id) : Promise.resolve(null)), [id]);
  const [open, setOpen] = useState(null);
  const [picked, setPicked] = useState({});
  const [q, setQ] = useState('');
  const [msg, setMsg] = useState(null);
  const [anim, setAnim] = useState(null);
  const [stepErr, setStepErr] = useState(null);
  const timer = useRef(null);
  const r = req.data;

  // auto run animation: when arriving from Intake (~run), light the agents up one by one
  useEffect(() => {
    setOpen(null); setStepErr(null);
    if (r && flag === 'run' && r.mode !== 'step') {
      let n = 0; setAnim(0);
      clearInterval(timer.current);
      timer.current = setInterval(() => { n += 1; setAnim(n); if (n >= r.stages.length) { clearInterval(timer.current); setAnim(null); go('journey/' + r.id); } }, 380);
    } else setAnim(null);
    return () => clearInterval(timer.current);
  }, [r && r.id]); // eslint-disable-line

  const runs = (list.data || []).filter((x) => !q || `${x.id} ${x.legalName} ${x.status} ${x.requestType}`.toLowerCase().includes(q.toLowerCase()));
  const chosen = Object.keys(picked).filter((k) => picked[k]);
  const afterDelete = (ids) => {
    setPicked({}); setMsg(`Deleted ${ids.length} run${ids.length > 1 ? 's' : ''}: ${ids.join(', ')}. Records they created were removed and changes they made were undone.`);
    if (ids.includes(id)) go('journey'); list.reload(); req.reload();
  };
  const delOne = async (x) => { if (window.confirm(`Delete ${x.id} (${x.legalName})? This also removes the record it created or undoes the change it made.`)) { await api.del('/requests/' + x.id); afterDelete([x.id]); } };
  const delMany = async (ids) => { if (ids.length && window.confirm(`Delete ${ids.length} run${ids.length > 1 ? 's' : ''}? Records they created are removed and their changes undone.`)) { await api.post('/requests/delete', { ids }); afterDelete(ids); } };
  const next = async () => { setStepErr(null); try { await api.post(`/requests/${r.id}/next`); req.reload(); list.reload(); } catch (e) { setStepErr(e.message); } };

  const shown = r ? (anim !== null ? anim : r.revealed ?? r.stages.length) : 0;
  const idxOf = (key) => (r ? r.stages.findIndex((s) => s.key === key) : -1);
  const visibleStages = r ? r.stages.slice(0, shown) : [];
  const st = r && (visibleStages.find((s) => s.key === open) || visibleStages[visibleStages.length - 1] || r.stages[0]);
  const people = visibleStages.filter((s) => s.actor === 'human').length;
  const policies = new Set(visibleStages.flatMap((s) => s.policies)).size;
  const finished = r && shown >= r.stages.length;
  const disclaimer = settings.data && settings.data.settings.disclaimer;
  const nextStage = r && r.mode === 'step' && (r.revealed < r.stages.length) ? r.stages[r.revealed] : null;
  const lastShown = r && r.stages[(r.revealed || 1) - 1];

  return (
    <>
      <Title eyebrow="AI agents" title="Request journey">
        Each request runs through the master data processes, then the MDM operations agents. Double-click an agent to see what it did; hover a rule to see the policy behind it.
      </Title>
      <Err error={list.error || req.error} />
      <div className="row">
        <div className="side" style={{ maxWidth: 330 }}>
          <div className="stack">
            <h2>Test runs ({(list.data || []).length})</h2>
            <label className="lbl" htmlFor="runs-q">Search runs</label>
            <input id="runs-q" type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="ID, party or status" />
            <div className="row" style={{ gap: 8 }}>
              <button type="button" className="btn" disabled={!chosen.length} onClick={() => delMany(chosen)}>Delete selected ({chosen.length})</button>
              <button type="button" className="btn" disabled={!runs.length} onClick={() => delMany(runs.map((x) => x.id))}>Delete all shown</button>
            </div>
            {msg && <div className="notice info small" role="status">{msg}</div>}
            {runs.map((x) => (
              <div key={x.id} className={'list-item' + (x.id === id ? ' on' : '')} style={{ flexDirection: 'row', alignItems: 'flex-start', gap: 10, padding: 10 }}>
                <input type="checkbox" aria-label={'Select ' + x.id} checked={!!picked[x.id]} onChange={(e) => setPicked({ ...picked, [x.id]: e.target.checked })} style={{ width: 20, height: 20, marginTop: 4 }} />
                <button type="button" onClick={() => go('journey/' + x.id)} style={{ flex: 1, minWidth: 0, border: 0, background: 'transparent', textAlign: 'left', padding: 0, display: 'flex', flexDirection: 'column', gap: 3 }}>
                  <span className="mono muted">{x.id} · {x.created}</span><strong>{x.legalName}</strong>
                  <span className="small muted">{x.requestType} · {x.mode === 'step' ? 'Agent by agent' : 'Auto run'}</span>
                  <span className={'tag ' + (x.status === 'Complete' ? (x.touchless ? 'agent' : 'ok') : 'human')} style={{ alignSelf: 'flex-start', borderRadius: 8, lineHeight: '16px' }}>{x.status === 'Complete' && x.touchless ? 'Complete · touchless' : x.status}</span>
                </button>
                <button type="button" className="btn" aria-label={'Delete ' + x.id} onClick={() => delOne(x)} style={{ height: 36, padding: '0 10px' }}>Delete</button>
              </div>
            ))}
            {list.data && list.data.length === 0 && <p className="muted">No test runs yet. Run one from <a href="#/intake">Intake</a>.</p>}
          </div>
        </div>

        {r && (
          <div className="grow stack">
            <div className="jhead">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, flex: '1 1 260px' }}>
                <span className="mono">{r.id} · {r.created} · {r.mode === 'step' ? 'Agent by agent' : 'Auto run'}</span>
                <h2>{r.legalName}</h2>
                <span style={{ fontSize: 13, color: '#C9D3E3' }}>{r.requestType} · <a href={`#/records/${r.recordId}`} style={{ color: '#9DB3EE' }}>{r.recordId}</a></span>
              </div>
              <div className="stat"><span className="s1">Status</span><span className="s2" style={{ fontSize: 14 }}>{r.status}</span></div>
              <div className="stat"><span className="s1">Touchless</span><span className="s2">{!finished && people === 0 ? 'So far' : r.touchless && finished ? 'Yes' : 'No'}</span></div>
              <div className="stat"><span className="s1">People</span><span className="s2">{people}</span></div>
              <div className="stat"><span className="s1">Policies</span><span className="s2">{policies}</span></div>
              <div className="stat"><span className="s1">Agent time</span><span className="s2">{r.elapsedMs != null ? (r.elapsedMs / 1000).toFixed(1) + 's' : '—'}</span></div>
            </div>

            {r.testData && disclaimer && <div className="disclaimer" role="note"><strong>Note</strong><span>{disclaimer} Test-data providers on this run: {(r.sources || []).filter((s) => s.mode === 'test').map((s) => s.source.replace(' · test data', '')).join(', ')}.</span></div>}
            {r.llm === false && <div className="notice warn">Claude is not configured, so Intake used the sample's key values.</div>}

            <div className="chevrons" aria-label="Stages">
              {GROUPS.map((g) => {
                const idxs = g.stages.map(idxOf);
                const states = idxs.map((i) => stateOf(r.stages[i], i, shown, anim !== null));
                const gs = states.includes('waiting') ? 'waiting' : states.includes('running') ? 'running' : states.every((x) => x === 'pending') ? 'pending' : states.some((x) => x === 'pending') ? 'running' : 'done';
                const done = states.filter((x) => x === 'done' || x === 'approved').length;
                return (
                  <div key={g.key} className={'chev ' + gs}>
                    <span className="t">{g.sub}</span><span className="n">{g.title}</span>
                    <span className="st">{gs === 'waiting' ? 'Waiting for a person' : `${done} of ${g.stages.length} done`}</span>
                  </div>
                );
              })}
            </div>

            <section className="card" style={{ padding: 20 }}>
              <div className="flow">
                {GROUPS.map((g) => (
                  <div key={g.key} className="lane" aria-label={g.title}>
                    <span className="small muted" style={{ fontWeight: 600, letterSpacing: '.05em', textTransform: 'uppercase', fontSize: 11 }}>{g.title}</span>
                    {g.stages.map((k) => {
                      const i = idxOf(k); const s = r.stages[i]; const state = stateOf(s, i, shown, anim !== null);
                      const visible = i < shown;
                      return (
                        <button type="button" key={k} disabled={!visible}
                          className={`anode ${visible ? s.actor : 'pending'} ${state === 'running' ? 'running' : ''} ${st && visible && st.key === k ? 'sel' : ''}`}
                          onClick={() => setOpen(k)} onDoubleClick={() => setOpen(k)} title={visible ? 'Double-click for detail' : 'Not run yet'} aria-pressed={!!(st && st.key === k)}>
                          {state === 'approved' && <span className="badge-tick" aria-label="Approved">✓</span>}
                          <span className="ic">{AGENT_ICON[k]}</span>
                          <span style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 0 }}>
                            <span className={'state ' + state}>{state === 'running' ? <span className="dots"><i /><i /><i /></span> : state === 'approved' ? <span className="tick">✓</span> : null}{STATE_LABEL[state]}</span>
                            <span className="nm">{s.name}</span>
                            {visible && <span className="st">{s.status}</span>}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                ))}
              </div>
            </section>

            {r.mode === 'step' && anim === null && (
              <div className="stepbar">
                {nextStage ? (<>
                  <span style={{ flex: '1 1 260px', fontSize: 14 }}>
                    {lastShown && lastShown.state === 'waiting' ? <><strong>{lastShown.name}</strong> is waiting for {lastShown.waitingFor}. Approve it below to continue.</> : <>Next agent: <strong>{nextStage.name}</strong></>}
                  </span>
                  <button type="button" className="btn dark" onClick={next} disabled={lastShown && lastShown.state === 'waiting'}>Run {nextStage.name}</button>
                </>) : <span style={{ fontSize: 14 }}>All agents have run.</span>}
                {stepErr && <span className="small" style={{ color: 'var(--red)' }}>{stepErr}</span>}
              </div>
            )}

            <div className="row">
              <div className="grow">{st && st.key && shown > 0 && anim === null && <StageDetail r={r} st={st} onChange={() => { req.reload(); list.reload(); }} />}</div>
              <aside className="card side" style={{ maxWidth: 340 }} aria-label="Decision trail">
                <h3>Decision trail</h3>
                <ol className="trail">
                  {visibleStages.map((s) => (
                    <li key={s.key} className={s.actor}><strong>{s.name}</strong> · {s.explanation || s.summary}
                      {s.state === 'approved' && <span className="small" style={{ color: '#0E5A32' }}> ✓ {s.status}</span>}</li>
                  ))}
                </ol>
              </aside>
            </div>
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
  const approval = st.state === 'approved' ? (st.sections.find((x) => x.title === 'Decision by a person') || {}).rows : null;
  return (
    <section aria-label="Stage detail" className="stack">
      <div className="card">
        <div className="row" style={{ alignItems: 'center', gap: 10 }}>
          <span className={'anode ' + st.actor} style={{ width: 'auto', padding: 0, border: 0, boxShadow: 'none', background: 'transparent' }}><span className="ic">{AGENT_ICON[st.key]}</span></span>
          <h2>{st.name}</h2>
          <span className={'tag ' + st.actor}>{st.actor === 'human' ? 'A person was needed' : 'Agent acted on its own'}</span>
          {st.state === 'waiting' && <span className="tag human">Waiting for {st.waitingFor}</span>}
          {st.state === 'approved' && <span className="tag ok">✓ {st.status}{approval && approval[0] ? ' · ' + approval[0].note : ''}</span>}
        </div>
        <p style={{ fontSize: 14, lineHeight: '21px' }}>{st.summary}</p>
        {st.explanation && <p className="small" style={{ lineHeight: '19px', color: 'var(--ink2)' }}><strong>Why:</strong> {st.explanation}</p>}
        <div className="row" style={{ gap: 6, alignItems: 'center' }}><span className="small muted">Policies considered</span>{st.policies.map((p) => <PolicyChip key={p} id={p} />)}</div>
        {st.state === 'waiting' && (
          <div className="row" style={{ alignItems: 'flex-end' }}>
            <div className="stack" style={{ gap: 4 }}><label className="lbl" htmlFor="who">Decided by</label><input id="who" type="text" value={who} onChange={(e) => setWho(e.target.value)} /></div>
            <div className="stack" style={{ gap: 4, flex: '1 1 240px' }}><label className="lbl" htmlFor="note">Note</label><input id="note" type="text" value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Called the owner to confirm the bank account" /></div>
            <button type="button" className="btn dark" onClick={approve}>✓ Approve</button>
          </div>
        )}
      </div>
      {st.key === 'intake' && r.uploadId && <UploadedEmail uid={r.uploadId} />}
      <Sections sections={st.sections} resetKey={r.id + st.key} />
    </section>
  );
}

function UploadedEmail({ uid }) {
  const u = useLoad(() => api.get('/uploads/' + uid), [uid]);
  if (!u.data) return null;
  return (<div className="stack"><h3>Email and attachments as received</h3><EmailPreview mail={u.data} /></div>);
}
