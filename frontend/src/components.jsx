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
