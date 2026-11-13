import React, { useEffect, useRef, useState } from 'react';
import { api, onAssist, getAssist } from './api.js';
import { PolicyChip } from './components.jsx';

const MODELS = ['claude-sonnet-5-5', 'claude-opus-5-5', 'claude-haiku-5-5'];

function suggestions(c) {
  if (c.requestId && c.stageKey === 'intake') return ['Why was this request blocked?', 'Which fields came from the attachments?', 'What happens if I reject it?'];
  if (c.requestId && c.stageKey === 'search') return ['Why did the best match score this?', 'Which policy sets the match threshold?', 'Is this a duplicate?'];
  if (c.requestId && c.stageKey === 'match') return ['Why was it linked or not merged?', 'Which policy decided this?', 'What happens if I edit the tax ID?'];
  if (c.requestId && c.stageKey === 'validate') return ['Why was this flagged?', 'Which checks used test data?', 'What does the steward need to confirm?'];
  if (c.requestId && ['legal', 'procurement', 'credit', 'tax'].includes(c.stageKey)) return ['Why did this need a person?', 'Which rule matched?', 'What changed on the record?'];
  if (c.requestId) return ['Why did this go to review?', 'Which policies applied?', 'What happens if I reject or edit?'];
  if (c.recordId) return ['Where did the payment terms come from?', 'Why did D&B win for the legal name?', 'Which sources feed this record?'];
  if (c.policyId) return ['Which agents use this policy?', 'What happens if I set it to H?', 'How do the rules decide?'];
  if (c.agent) return ['Which policies does this agent read?', 'When does it stop for a person?', 'Which data providers does it use?'];
  return ['What does each application do?', 'What is a Business ready record?', 'Where do I start a request?'];
}

/** Read-only assistant: explains and points to screens, grounded in the decision trace, records and policies. */
export default function Assistant() {
  const [open, setOpen] = useState(false);
  const [ctx, setCtx] = useState(getAssist());
  const [q, setQ] = useState('');
  const [model, setModel] = useState(MODELS[0]);
  const [log, setLog] = useState([]);
  const [busy, setBusy] = useState(false);
  const end = useRef(null);
  useEffect(() => onAssist(setCtx), []);
  useEffect(() => { if (end.current) end.current.scrollIntoView({ block: 'end' }); }, [log, busy]);

  const ask = async (question) => {
    if (!question.trim()) return;
    setQ(''); setBusy(true);
    const entry = { q: question, where: ctx.label || ctx.page };
    setLog((l) => [...l, entry]);
    try {
      const r = await api.post('/assistant', { question, model, ...ctx });
      setLog((l) => l.map((e) => (e === entry ? { ...e, a: r.answer, policies: r.policies } : e)));
    } catch (e) {
      setLog((l) => l.map((x) => (x === entry ? { ...x, err: e.message } : x)));
    } finally { setBusy(false); }
  };

  if (!open) return <button type="button" className="assist-fab" onClick={() => setOpen(true)} aria-label="Open the assistant">✦ Ask</button>;
  return (
    <aside className="assist" aria-label="Assistant">
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
        <strong>Assistant</strong>
        <span className="row" style={{ gap: 6, alignItems: 'center' }}>
          <label className="lbl" htmlFor="am" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden' }}>Model</label>
          <select id="am" value={model} onChange={(e) => setModel(e.target.value)} style={{ height: 32, fontSize: 12, padding: '0 6px' }}>{MODELS.map((m) => <option key={m}>{m}</option>)}</select>
          <button type="button" className="btn" style={{ height: 32 }} onClick={() => setOpen(false)} aria-label="Close the assistant">✕</button>
        </span>
      </div>
      <span className="small muted">Looking at: {ctx.label || ctx.page || 'this screen'} · explains only, never changes anything</span>
      <div className="assist-log">
        {log.length === 0 && <p className="small muted">Ask about what you see. Answers come from the decision trace, records and policies, and cite the policy IDs.</p>}
        {log.map((e, i) => (
          <div key={i} className="stack" style={{ gap: 4 }}>
            <div className="assist-q">{e.q}</div>
            {e.a && <div className="assist-a">{e.a}{(e.policies || []).length > 0 && <div className="row" style={{ gap: 4, marginTop: 6 }}>{e.policies.map((p) => <a key={p} href="#/policies" style={{ textDecoration: 'none' }}><PolicyChip id={p} /></a>)}</div>}</div>}
            {e.err && <div className="assist-a" style={{ color: 'var(--red)' }}>{e.err}</div>}
          </div>
        ))}
        {busy && <div className="assist-a"><span className="dots"><i /><i /><i /></span></div>}
        <span ref={end} />
      </div>
      <div className="row" style={{ gap: 6 }}>{suggestions(ctx).map((s) => <button type="button" key={s} className="schip" onClick={() => ask(s)} disabled={busy}>{s}</button>)}</div>
      <form className="row" style={{ gap: 6 }} onSubmit={(e) => { e.preventDefault(); ask(q); }}>
        <label htmlFor="aq" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden' }}>Question</label>
        <input id="aq" type="text" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask about this screen…" style={{ flex: 1 }} />
        <button type="submit" className="btn dark" disabled={busy || !q.trim()}>Ask</button>
      </form>
    </aside>
  );
}
