import React, { useState } from 'react';
import { api, clearPolicyCache } from '../api.js';
import { Err } from '../components.jsx';

const ALL = 'All agents';
const list = (s) => String(s || '').split(',').map((x) => x.trim()).filter(Boolean);

function Src({ fs, k }) {
  const s = fs && fs[k];
  if (!s) return null;
  if (s.from === 'document') return <span className="src doc" title={s.quote ? `From the document: “${s.quote}”` : 'From the document'}>From document{s.confidence ? ` · ${Math.round(s.confidence * 100)}%` : ''}</span>;
  if (s.from === 'governance') return <span className="src gov">Needs governance input</span>;
  if (s.from === 'edited') return <span className="src ed">Edited</span>;
  return null;
}

function Field({ label, k, fs, children, wide, req }) {
  return (
    <div className={'f' + (fs && fs[k] && fs[k].from === 'governance' ? ' needs' : '')} style={wide ? { gridColumn: '1 / -1' } : undefined}>
      <span className="lbl" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>{label}{req && <span aria-hidden="true" style={{ color: 'var(--red)' }}>*</span>}<Src fs={fs} k={k} /></span>
      {children}
    </div>
  );
}

function Section({ n, title, sub, children }) {
  return (
    <section className="fsec">
      <div className="fsec-h"><span className="fnum">{n}</span><div><h3>{title}</h3>{sub && <span className="small muted">{sub}</span>}</div></div>
      {children}
    </section>
  );
}

/** One form for every policy: identity, scope, inputs, rules, values, autonomy, precedence, evidence, test cases. */
export default function PolicyForm({ p, meta, onSaved, onCancel }) {
  const [f, setF] = useState(() => JSON.parse(JSON.stringify(p)));
  const [txt, setTxt] = useState({ roles: (p.roles || []).join(', '), regions: (p.regions || []).join(', ') });
  const [err, setErr] = useState(null);
  const [tests, setTests] = useState(null);
  const fs = f.fieldSources || {};
  const set = (k, v) => setF({ ...f, [k]: v });
  const attrs = Object.keys(meta.attributes || {});

  const body = (status) => ({
    title: f.title, folder: f.folder, stage: f.stage, owner: f.owner, steward: f.steward, effective: f.effective, effectiveTo: f.effectiveTo, status,
    appliesTo: f.appliesTo, roles: list(txt.roles), recordTypes: f.recordTypes, regions: list(txt.regions), triggers: f.triggers,
    inputs: f.inputs, rules: f.rules, params: f.params, rows: f.rows, level: f.level, approverRole: f.approverRole, escalation: f.escalation,
    slaHours: Number(f.slaHours) || 0, priority: Number(f.priority) || 0, complianceFloor: !!f.complianceFloor, citationRequired: !!f.citationRequired,
    text: f.text, exceptions: f.exceptions, source: f.source, testCases: f.testCases,
  });
  const save = async (status) => {
    setErr(null);
    try { const s = await api.put('/policies/' + p.id, body(status)); clearPolicyCache(); onSaved(s); } catch (e) { setErr(e.message); }
  };
  const runTests = async () => { setErr(null); try { setTests((await api.post(`/policies/${p.id}/test`, body(f.status))).results); } catch (e) { setErr(e.message); } };

  const toggle = (k, v) => { const cur = f[k] || []; set(k, cur.includes(v) ? cur.filter((x) => x !== v) : [...cur, v]); };
  const toggleAgent = (a) => {
    let cur = f.appliesTo || [];
    if (a === ALL) cur = cur.includes(ALL) ? [] : [ALL];
    else cur = cur.includes(a) ? cur.filter((x) => x !== a) : [...cur.filter((x) => x !== ALL), a];
    set('appliesTo', cur);
  };
  const upd = (k, i, patch) => set(k, (f[k] || []).map((x, j) => (j === i ? (Array.isArray(x) ? patch : { ...x, ...patch }) : x)));
  const del = (k, i) => set(k, (f[k] || []).filter((_, j) => j !== i));
  const rule = (i, patch) => upd('rules', i, patch);
  const cond = (i, ci, patch) => rule(i, { when: f.rules[i].when.map((c, j) => (j === ci ? { ...c, ...patch } : c)) });
  const outs = (r) => Object.entries(r.then || {});
  const setOut = (i, entries) => rule(i, { then: Object.fromEntries(entries.filter(([k]) => k !== '')) });

  const missing = (meta.required || []).filter((k) => !f[k] || (Array.isArray(f[k]) && !f[k].length));
  if (!((f.rules || []).length || (f.rows || []).length || (f.params || []).length)) missing.push('rules');
  const score = Math.round((100 * ((meta.required || []).length + 1 - missing.length)) / ((meta.required || []).length + 1));
  const govCount = Object.values(fs).filter((x) => x.from === 'governance').length;

  return (
    <article className="card grow pform" aria-label={'Policy form ' + p.id}>
      <div className="row" style={{ alignItems: 'center', gap: 10 }}>
        <span className="mono muted">{p.id} · v{p.version}</span><h2>{f.title || 'Untitled policy'}</h2>
        <span className="small muted">{f.status === 'Draft' ? 'Draft: agents do not read it until it is activated' : 'Saving publishes the next version; agents use it from the next request'}</span>
      </div>
      <div className="complete" aria-label={`Form ${score}% complete`}>
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
          <strong className="small">Form {score}% complete</strong>
          <span className="small muted">{missing.length ? 'Required to activate: ' + missing.join(', ') : 'All required fields filled'}{govCount ? ` · ${govCount} field${govCount > 1 ? 's' : ''} not in the document need governance input` : ''}</span>
        </div>
        <span className="meter"><i style={{ width: score + '%', background: score === 100 ? '#1E8A4C' : undefined }} /></span>
      </div>
      <Err error={err} />

      <Section n="1" title="Identity" sub="What the policy is and who owns it">
        <div className="form">
          <Field label="Title" k="title" fs={fs} wide req><input type="text" value={f.title || ''} onChange={(e) => set('title', e.target.value)} /></Field>
          <Field label="Category" k="folder" fs={fs}><select value={f.folder} onChange={(e) => set('folder', e.target.value)}>{meta.folders.map((x) => <option key={x.key} value={x.key}>{x.name}</option>)}</select></Field>
          <Field label="Owner" k="owner" fs={fs} req><input type="text" value={f.owner || ''} onChange={(e) => set('owner', e.target.value)} /></Field>
          <Field label="Data steward" k="steward" fs={fs}><input type="text" value={f.steward || ''} onChange={(e) => set('steward', e.target.value)} /></Field>
          <Field label="Effective from" k="effective" fs={fs} req><input type="text" value={f.effective || ''} onChange={(e) => set('effective', e.target.value)} placeholder="YYYY-MM-DD" /></Field>
          <Field label="Effective to (optional)" k="effectiveTo" fs={fs}><input type="text" value={f.effectiveTo || ''} onChange={(e) => set('effectiveTo', e.target.value)} placeholder="YYYY-MM-DD" /></Field>
          <Field label="Stage" k="stage" fs={fs}><input type="text" value={f.stage || ''} onChange={(e) => set('stage', e.target.value)} /></Field>
        </div>
      </Section>

      <Section n="2" title="Scope" sub="Which agents and people it applies to, and when">
        <Field label="Applies to agents" k="appliesTo" fs={fs} req>
          <div className="row" style={{ gap: 8 }}>{meta.agents.map((a) => <label key={a} className={'agentpick' + ((f.appliesTo || []).includes(a) ? ' on' : '')}><input type="checkbox" checked={(f.appliesTo || []).includes(a)} onChange={() => toggleAgent(a)} />{a}</label>)}</div>
        </Field>
        <div className="form">
          <Field label="People's roles (comma-separated)" k="roles" fs={fs}><input type="text" value={txt.roles} onChange={(e) => setTxt({ ...txt, roles: e.target.value })} /></Field>
          <Field label="Regions (comma-separated)" k="regions" fs={fs}><input type="text" value={txt.regions} onChange={(e) => setTxt({ ...txt, regions: e.target.value })} /></Field>
          <Field label="Record types" k="recordTypes" fs={fs}><div className="row" style={{ gap: 8 }}>{['Customer', 'Supplier'].map((x) => <label key={x} className={'agentpick' + ((f.recordTypes || []).includes(x) ? ' on' : '')}><input type="checkbox" checked={(f.recordTypes || []).includes(x)} onChange={() => toggle('recordTypes', x)} />{x}</label>)}</div></Field>
          <Field label="Runs on" k="triggers" fs={fs}><div className="row" style={{ gap: 8 }}>{['Create', 'Change', 'Periodic'].map((x) => <label key={x} className={'agentpick' + ((f.triggers || []).includes(x) ? ' on' : '')}><input type="checkbox" checked={(f.triggers || []).includes(x)} onChange={() => toggle('triggers', x)} />{x}</label>)}</div></Field>
        </div>
      </Section>

      <Section n="3" title="Statement" sub="The policy in plain English, for people">
        <Field label="In plain English" k="text" fs={fs} wide req><textarea rows={4} value={f.text || ''} onChange={(e) => set('text', e.target.value)} /></Field>
      </Section>

      <Section n="4" title="Inputs" sub="Data the policy reads, and where it comes from">
        {(f.inputs || []).map((x, i) => (
          <div key={i} className="row" style={{ gap: 8, alignItems: 'flex-end' }}>
            <div className="f" style={{ flex: '1 1 200px' }}><label className="lbl" htmlFor={'ia' + i}>Attribute</label><input id={'ia' + i} type="text" list="attrs" value={x.attribute} onChange={(e) => upd('inputs', i, { attribute: e.target.value })} /></div>
            <div className="f" style={{ flex: '1 1 200px' }}><label className="lbl" htmlFor={'is' + i}>Source</label><input id={'is' + i} type="text" value={x.source} onChange={(e) => upd('inputs', i, { source: e.target.value })} /></div>
            <button type="button" className="btn" onClick={() => del('inputs', i)}>Remove</button>
          </div>
        ))}
        <button type="button" className="btn" style={{ alignSelf: 'flex-start' }} onClick={() => set('inputs', [...(f.inputs || []), { attribute: '', source: '' }])}>Add input</button>
      </Section>

      <Section n="5" title="Rules" sub={f.engine ? 'The agents run these rules. First match wins; a rule with no conditions is the default.' : 'Conditions and actions'}>
        <Src fs={fs} k="rules" />
        <datalist id="attrs">{attrs.map((a) => <option key={a} value={a}>{meta.attributes[a]}</option>)}</datalist>
        {(f.rules || []).map((r, i) => (
          <div key={i} className="rulebox">
            <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}><strong className="small">Rule {i + 1}{!(r.when || []).length ? ' · default' : ''}</strong>
              <span className="row" style={{ gap: 6 }}>
                <button type="button" className="btn" disabled={i === 0} onClick={() => { const rs = [...f.rules]; [rs[i - 1], rs[i]] = [rs[i], rs[i - 1]]; set('rules', rs); }} aria-label="Move rule up">↑</button>
                <button type="button" className="btn" onClick={() => del('rules', i)}>Remove rule</button></span></div>
            <span className="small muted">When all of these hold</span>
            {(r.when || []).map((c, ci) => (
              <div key={ci} className="row" style={{ gap: 6, alignItems: 'center' }}>
                <input type="text" list="attrs" aria-label="Attribute" value={c.attr} onChange={(e) => cond(i, ci, { attr: e.target.value })} style={{ flex: '2 1 180px' }} />
                <select aria-label="Operator" value={c.op} onChange={(e) => cond(i, ci, { op: e.target.value })} style={{ flex: '0 0 120px' }}>{(meta.ops || []).map((o) => <option key={o}>{o}</option>)}</select>
                {!['exists', 'not exists'].includes(c.op) && <input type="text" aria-label="Value" value={c.value === null || c.value === undefined ? '' : String(c.value)} onChange={(e) => cond(i, ci, { value: e.target.value })} style={{ flex: '1 1 140px' }} placeholder="value or ${name}" />}
                <button type="button" className="btn" onClick={() => rule(i, { when: r.when.filter((_, j) => j !== ci) })} aria-label="Remove condition">✕</button>
              </div>
            ))}
            <button type="button" className="btn" style={{ alignSelf: 'flex-start' }} onClick={() => rule(i, { when: [...(r.when || []), { attr: '', op: '=', value: '' }] })}>Add condition</button>
            <span className="small muted">Then set</span>
            {outs(r).map(([k, val], oi) => (
              <div key={oi} className="row" style={{ gap: 6 }}>
                <input type="text" aria-label="Output attribute" value={k} onChange={(e) => setOut(i, outs(r).map((x, j) => (j === oi ? [e.target.value, x[1]] : x)))} style={{ flex: '1 1 160px' }} />
                <input type="text" aria-label="Output value" value={String(val)} onChange={(e) => setOut(i, outs(r).map((x, j) => (j === oi ? [x[0], e.target.value] : x)))} style={{ flex: '2 1 200px' }} />
              </div>
            ))}
            <button type="button" className="btn" style={{ alignSelf: 'flex-start' }} onClick={() => rule(i, { then: { ...(r.then || {}), ['new_attribute']: '' } })}>Add output</button>
            <div className="row" style={{ gap: 8 }}>
              <div className="f" style={{ flex: '1 1 200px' }}><label className="lbl" htmlFor={'db' + i}>Decided by</label><input id={'db' + i} type="text" value={r.decidedBy || ''} onChange={(e) => rule(i, { decidedBy: e.target.value })} placeholder="Agent, or a role" /></div>
              <div className="f" style={{ flex: '2 1 260px' }}><label className="lbl" htmlFor={'nt' + i}>Note</label><input id={'nt' + i} type="text" value={r.note || ''} onChange={(e) => rule(i, { note: e.target.value })} /></div>
            </div>
          </div>
        ))}
        <div className="row" style={{ gap: 8 }}>
          <button type="button" className="btn" onClick={() => setF({ ...f, engine: true, rules: [...(f.rules || []), { when: [{ attr: '', op: '=', value: '' }], then: {}, decidedBy: 'Agent', note: '' }] })}>Add rule</button>
          {(f.rows || []).length > 0 && <span className="small muted" style={{ alignSelf: 'center' }}>{f.rows.length} descriptive condition row{f.rows.length > 1 ? 's' : ''} kept from the original policy text.</span>}
        </div>
      </Section>

      <Section n="6" title="Values" sub="Thresholds and limits the rules and agents use, written ${name} in rules">
        {(f.params || []).map((x, i) => (
          <div key={i} className="row" style={{ alignItems: 'flex-end', gap: 8 }}>
            <div className="f" style={{ flex: '1 1 180px' }}><label className="lbl" htmlFor={'pk' + i}>Name</label><input id={'pk' + i} type="text" value={x.key} onChange={(e) => upd('params', i, { key: e.target.value })} /></div>
            <div className="f" style={{ flex: '0 1 150px' }}><label className="lbl" htmlFor={'pv' + i}>Value</label><input id={'pv' + i} type="text" value={x.value} onChange={(e) => upd('params', i, { value: e.target.value })} /></div>
            <div className="f" style={{ flex: '2 1 240px' }}><label className="lbl" htmlFor={'ph' + i}>What it controls</label><input id={'ph' + i} type="text" value={x.help || ''} onChange={(e) => upd('params', i, { help: e.target.value })} /></div>
            <button type="button" className="btn" onClick={() => del('params', i)}>Remove</button>
          </div>
        ))}
        <button type="button" className="btn" style={{ alignSelf: 'flex-start' }} onClick={() => set('params', [...(f.params || []), { key: '', value: '', help: '' }])}>Add value</button>
      </Section>

      <Section n="7" title="Autonomy" sub="Who decides, and what happens when a person is needed">
        <div className="form">
          <Field label="Autonomy level" k="level" fs={fs} req><select value={f.level} onChange={(e) => set('level', e.target.value)}>{Object.entries(meta.levels).map(([k, v]) => <option key={k} value={k}>{k} · {v}</option>)}</select></Field>
          <Field label="Approver role" k="approverRole" fs={fs}><input type="text" value={f.approverRole || ''} onChange={(e) => set('approverRole', e.target.value)} /></Field>
          <Field label="Escalation" k="escalation" fs={fs}><input type="text" value={f.escalation || ''} onChange={(e) => set('escalation', e.target.value)} placeholder="e.g. BU finance director after 2 days" /></Field>
          <Field label="Response time (hours)" k="slaHours" fs={fs}><input type="text" value={f.slaHours ?? ''} onChange={(e) => set('slaHours', e.target.value)} /></Field>
        </div>
      </Section>

      <Section n="8" title="Precedence" sub="Which policy wins when two disagree">
        <div className="form">
          <Field label="Priority (lower wins)" k="priority" fs={fs}><input type="text" value={f.priority ?? ''} onChange={(e) => set('priority', e.target.value)} /></Field>
          <Field label="Compliance floor" k="complianceFloor" fs={fs}><label className="toggle"><input type="checkbox" checked={!!f.complianceFloor} onChange={(e) => set('complianceFloor', e.target.checked)} /><span className="tr" aria-hidden="true" />{f.complianceFloor ? 'Other policies can only make it stricter' : 'Off'}</label></Field>
        </div>
      </Section>

      <Section n="9" title="Evidence" sub="Where the policy comes from and how decisions are recorded">
        <div className="form">
          <Field label="Source or regulation" k="source" fs={fs} wide><input type="text" value={f.source || ''} onChange={(e) => set('source', e.target.value)} /></Field>
          <Field label="Exceptions" k="exceptions" fs={fs} wide><textarea rows={2} value={f.exceptions || ''} onChange={(e) => set('exceptions', e.target.value)} /></Field>
          <Field label="Citation on every decision" k="citationRequired" fs={fs}><label className="toggle"><input type="checkbox" checked={!!f.citationRequired} onChange={(e) => set('citationRequired', e.target.checked)} /><span className="tr" aria-hidden="true" />{f.citationRequired ? 'Required' : 'Not required'}</label></Field>
        </div>
      </Section>

      <Section n="10" title="Test cases" sub="Example inputs and the expected outcome; run them before you save">
        {(f.testCases || []).map((t, i) => (
          <div key={i} className="row" style={{ gap: 8, alignItems: 'flex-end' }}>
            <div className="f" style={{ flex: '1 1 160px' }}><label className="lbl" htmlFor={'tn' + i}>Name</label><input id={'tn' + i} type="text" value={t.name} onChange={(e) => upd('testCases', i, { name: e.target.value })} /></div>
            <div className="f" style={{ flex: '2 1 240px' }}><label className="lbl" htmlFor={'ti' + i}>Inputs (JSON)</label><input id={'ti' + i} type="text" className="mono" defaultValue={JSON.stringify(t.inputs)} onBlur={(e) => { try { upd('testCases', i, { inputs: JSON.parse(e.target.value) }); } catch { setErr('Test inputs must be JSON, e.g. {"proposed_limit": 40000}'); } }} /></div>
            <div className="f" style={{ flex: '2 1 200px' }}><label className="lbl" htmlFor={'te' + i}>Expected (JSON)</label><input id={'te' + i} type="text" className="mono" defaultValue={JSON.stringify(t.expect)} onBlur={(e) => { try { upd('testCases', i, { expect: JSON.parse(e.target.value) }); } catch { setErr('Expected outcome must be JSON, e.g. {"decidedBy": "Agent"}'); } }} /></div>
            <button type="button" className="btn" onClick={() => del('testCases', i)}>Remove</button>
          </div>
        ))}
        <div className="row" style={{ gap: 8 }}>
          <button type="button" className="btn" onClick={() => set('testCases', [...(f.testCases || []), { name: 'New case', inputs: {}, expect: { decidedBy: 'Agent' } }])}>Add test case</button>
          <button type="button" className="btn dark" disabled={!(f.rules || []).length} onClick={runTests}>Run test cases</button>
        </div>
        {tests && <ul className="checks">{tests.map((t, i) => <li key={i} className={t.passed ? 'ok' : 'fail'}><span className="mark">{t.passed ? '✓ Passed' : '✕ Failed'}</span><span style={{ flex: '1 1 260px' }}>{t.name}<span className="muted"> · matched “{t.rule}” · got {JSON.stringify(t.got)}</span></span></li>)}</ul>}
      </Section>

      <div className="row" style={{ gap: 8, position: 'sticky', bottom: 0, background: '#fff', padding: '12px 0', borderTop: '1px solid var(--line)' }}>
        <button type="button" className="btn dark" disabled={missing.length > 0} onClick={() => save('Active')} title={missing.length ? 'Fill the required fields first' : ''}>{p.status === 'Active' ? 'Save and publish' : 'Activate'}</button>
        {p.status !== 'Active' && <button type="button" className="btn" onClick={() => save('Draft')}>Save draft</button>}
        <button type="button" className="btn" onClick={onCancel}>Cancel</button>
      </div>
    </article>
  );
}
