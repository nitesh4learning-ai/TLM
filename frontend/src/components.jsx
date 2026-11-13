import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { policyMap } from './api.js';

let cache = {};
export function usePolicies() {
  const [m, setM] = useState(cache);
  useEffect(() => { policyMap().then((x) => { cache = x; setM(x); }).catch(() => {}); }, []);
  return m;
}

function PolicyTip({ p, id }) {
  if (!p) return <span>{id}</span>;
  return (<><strong>{id} · {p.title}</strong> <span style={{ opacity: .7 }}>v{p.version}</span><br />{p.text}<br /><span className="lv">Autonomy {p.level} · {p.levelName}</span><br /><span style={{ opacity: .8 }}>Applies to: {(p.appliesTo || [p.agent]).join(', ')}</span></>);
}

/** Hover or focus anywhere on the wrapped element shows a tooltip that always stays inside the window. */
export function HoverTip({ content, children, as = 'span', className, style, ...rest }) {
  const [pos, setPos] = useState(null);
  const show = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    const w = Math.min(340, window.innerWidth - 24);
    let left = Math.min(Math.max(12, r.left), window.innerWidth - w - 12);
    const below = r.bottom + 8, above = r.top - 8;
    setPos({ left, top: below, above, w, flip: window.innerHeight - r.bottom < 180 });
  };
  const Tag = as;
  return (
    <Tag className={className} style={style} tabIndex={0} onMouseEnter={show} onMouseLeave={() => setPos(null)} onFocus={show} onBlur={() => setPos(null)} {...rest}>
      {children}
      {pos && content && createPortal(
        <div className="htip" role="tooltip" style={{ left: pos.left, width: pos.w, ...(pos.flip ? { bottom: window.innerHeight - pos.above } : { top: pos.top }) }}>{content}</div>,
        document.body)}
    </Tag>
  );
}

export function PolicyChip({ id }) {
  const m = usePolicies();
  if (!id) return null;
  return <HoverTip className="chip2" content={<PolicyTip p={m[id]} id={id} />} aria-label={m[id] ? `${id}: ${m[id].title}` : id}>{id}</HoverTip>;
}

export function usePolicyTip() {
  const m = usePolicies();
  return (id) => (id ? <PolicyTip p={m[id]} id={id} /> : null);
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
  const tip = usePolicyTip();
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
          return (<HoverTip as="li" key={i} className={cls} content={tip(r.policy)}><span className="mark">{mark}</span><span style={{ flex: '1 1 260px' }}>{r.k}<span className="muted"> · {r.note}</span></span>{r.policy && <span className="chip2">{r.policy}</span>}</HoverTip>);
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

const P = (d) => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{d}</svg>;
export const AGENT_ICON = {
  intake: P(<><path d="M4 13l2-7h12l2 7" /><path d="M4 13v5h16v-5h-5a3 3 0 0 1-6 0H4z" /></>),
  search: P(<><circle cx="11" cy="11" r="6.5" /><path d="M20 20l-4-4" /></>),
  match: P(<><circle cx="8" cy="12" r="4.5" /><circle cx="16" cy="12" r="4.5" /></>),
  enrich: P(<><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" /><path d="M19 17l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z" /></>),
  validate: P(<><path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z" /><path d="M9 12l2 2 4-4" /></>),
  legal: P(<><path d="M12 4v16M5 20h14M6 8h12" /><path d="M6 8l-3 6a3 3 0 0 0 6 0zM18 8l-3 6a3 3 0 0 0 6 0z" /></>),
  procurement: P(<><path d="M4 5h2l2.2 10.5a1.5 1.5 0 0 0 1.5 1.2h7.6a1.5 1.5 0 0 0 1.5-1.1L20.5 9H7" /><circle cx="10" cy="20" r="1.2" /><circle cx="17" cy="20" r="1.2" /></>),
  credit: P(<><rect x="3" y="6" width="18" height="13" rx="2" /><path d="M3 10h18M7 15h4" /></>),
  tax: P(<><path d="M6 3h9l4 4v14H6z" /><path d="M9 13l6-4M9.5 9.5h.01M14.5 13.5h.01" /></>),
  record: P(<><rect x="4" y="3" width="16" height="18" rx="2" /><path d="M8 8h8M8 12h8M8 16h5" /></>),
  orchestrator: P(<><circle cx="12" cy="12" r="3" /><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" /></>),
  copilot: P(<><circle cx="12" cy="8" r="3.5" /><path d="M5 20c1-3.8 3.8-6 7-6s6 2.2 7 6" /></>),
  lifecycle: P(<><path d="M20 12a8 8 0 1 1-2.3-5.7" /><path d="M20 4v4h-4" /></>),
  outreach: P(<><path d="M4 5h16v11H8l-4 4z" /></>),
};
