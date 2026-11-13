import React, { useEffect, useState } from 'react';
import { policyMap } from './api.js';

let cache = {};
export function usePolicies() {
  const [m, setM] = useState(cache);
  useEffect(() => { policyMap().then((x) => { cache = x; setM(x); }).catch(() => {}); }, []);
  return m;
}

export function PolicyChip({ id }) {
  const m = usePolicies();
  const p = m[id];
  if (!id) return null;
  return (
    <span className="chip" tabIndex={0} aria-label={p ? `${id}: ${p.title}` : id}>
      {id}
      <span className="tip" role="tooltip">
        {p ? (<><strong>{id} · {p.title}</strong><br />Autonomy {p.level} · {p.levelName}<br />Agent: {p.agent} · Owner: {p.owner}<br />{p.text}</>) : id}
      </span>
    </span>
  );
}

export function Title({ eyebrow, title, children, right }) {
  return (
    <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-end' }}>
      <div className="title"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1>{children && <p>{children}</p>}</div>
      {right}
    </div>
  );
}

function Cell({ c }) {
  return (<td className={c.win ? 'win' : ''}>{c.v}{c.policy ? <> <PolicyChip id={c.policy} /></> : null}</td>);
}

function Section({ s }) {
  return (
    <section className="card">
      <div className="row" style={{ justifyContent: 'space-between', gap: 8 }}><h3>{s.title}</h3><span className="small muted">{s.meta}</span></div>
      {s.kind === 'text' && <p style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: '20px' }}>{s.text}</p>}
      {s.kind === 'kv' && (
        <div className="kv">{s.rows.map((r, i) => (
          <div key={i}><div className="k">{r.k}</div><div className="v">{r.v}</div><div className="n">{r.note}{r.policy && <PolicyChip id={r.policy} />}</div></div>
        ))}</div>
      )}
      {s.kind === 'table' && (
        <div className="scroll"><table><thead><tr>{s.cols.map((c) => <th key={c} scope="col">{c}</th>)}</tr></thead>
          <tbody>{s.rows.map((r, i) => <tr key={i}>{r.cells.map((c, j) => <Cell key={j} c={c} />)}</tr>)}</tbody></table></div>
      )}
      {s.kind === 'checks' && (
        <ul className="checks">{s.rows.map((r, i) => {
          const cls = r.pass === true ? 'ok' : r.pass === 'human' ? 'person' : 'fail';
          const mark = r.pass === true ? '✓ Passed' : r.pass === 'human' ? '● Person' : '✕ Not met';
          return (<li key={i} className={cls}><span className="mark">{mark}</span><span style={{ flex: '1 1 260px' }}>{r.k}<span className="muted"> · {r.note}</span></span><PolicyChip id={r.policy} /></li>);
        })}</ul>
      )}
    </section>
  );
}

/** Progressive disclosure: level-1 sections first, then "…" opens the next level. */
export function Sections({ sections, resetKey }) {
  const [depth, setDepth] = useState(1);
  useEffect(() => setDepth(1), [resetKey]);
  const max = Math.max(1, ...sections.map((s) => s.level || 1));
  return (
    <div className="stack">
      {sections.filter((s) => (s.level || 1) <= depth).map((s, i) => <Section key={i} s={s} />)}
      {depth < max && <button type="button" className="more" onClick={() => setDepth(depth + 1)}><span aria-hidden="true" style={{ fontSize: 18 }}>…</span>Show more detail (level {depth + 1} of {max})</button>}
      {depth > 1 && depth >= max && <button type="button" className="btn" style={{ alignSelf: 'flex-start' }} onClick={() => setDepth(1)}>Show less</button>}
    </div>
  );
}

export function useLoad(fn, deps) {
  const [state, set] = useState({ data: null, error: null, loading: true });
  const reload = () => { set((s) => ({ ...s, loading: true })); fn().then((data) => set({ data, error: null, loading: false })).catch((e) => set({ data: null, error: e.message, loading: false })); };
  useEffect(reload, deps); // eslint-disable-line
  return { ...state, reload };
}

export function Err({ error }) { return error ? <div className="notice err" role="alert">{error}</div> : null; }

const kb = (n) => (n > 1024 * 1024 ? (n / 1024 / 1024).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB');

/** Shows an email (headers, full thread) and its attachments, with PDFs viewable inline. */
export function EmailPreview({ mail }) {
  const [open, setOpen] = useState(null);
  useEffect(() => setOpen(mail.attachments.length ? mail.attachments[0].name : null), [mail.id]);
  const cur = mail.attachments.find((a) => a.name === open);
  const isPdf = cur && cur.name.toLowerCase().endsWith('.pdf');
  return (
    <div className="stack">
      <section className="card" aria-label="Email">
        <div className="kv">
          <div><div className="k">From</div><div className="v">{mail.from || '—'}</div></div>
          <div><div className="k">To</div><div className="v">{mail.to || '—'}</div></div>
          <div><div className="k">Date</div><div className="v">{mail.date || '—'}</div></div>
        </div>
        <div><div className="small muted">Subject</div><h3>{mail.subject || '(no subject)'}</h3></div>
        <div className="mailbody">{mail.body || '(no text in the email body)'}</div>
      </section>
      <section className="card" aria-label="Attachments">
        <h3>Attachments ({mail.attachments.length})</h3>
        {mail.attachments.length === 0 && <p className="small muted">No attachments.</p>}
        <div className="row" style={{ gap: 8 }}>
          {mail.attachments.map((a) => (
            <button type="button" key={a.name} className={'att' + (a.name === open ? ' on' : '')} aria-pressed={a.name === open} onClick={() => setOpen(a.name)}>
              <span className="atticon" aria-hidden="true">{a.name.split('.').pop().toUpperCase()}</span>
              <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}><strong style={{ fontSize: 13 }}>{a.name}</strong><span className="small muted">{kb(a.bytes)}</span></span>
            </button>
          ))}
        </div>
        {cur && (
          <div className="stack" style={{ gap: 8 }}>
            <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
              <strong className="small">{cur.name}</strong>
              <a className="btn" href={cur.url} target="_blank" rel="noreferrer">Open in new tab</a>
            </div>
            {isPdf ? <iframe title={cur.name} src={cur.url} className="pdfview" /> : <iframe title={cur.name} src={cur.url} className="pdfview" style={{ height: 320 }} />}
          </div>
        )}
      </section>
    </div>
  );
}
