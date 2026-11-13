import React, { useState } from 'react';
import { api, go } from '../api.js';
import { Title, useLoad, Err, EmailPreview } from '../components.jsx';

export default function Intake() {
  const sc = useLoad(() => api.get('/scenarios'), []);
  const [files, setFiles] = useState([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState(null);
  const [over, setOver] = useState(false);
  const [preview, setPreview] = useState(null);
  const [mode, setMode] = useState('auto');

  const run = async (label, fn) => {
    setBusy(label); setError(null);
    try { const r = await fn(); go('journey/' + r.id + (mode === 'auto' ? '~run' : '')); } catch (e) { setError(e.message); } finally { setBusy(''); }
  };
  const load = async (fs) => {
    const all = [...files, ...fs];
    setFiles(all); setError(null); setBusy('Reading the upload');
    try { setPreview(await api.upload('/uploads', all)); } catch (e) { setError(e.message); setPreview(null); } finally { setBusy(''); }
  };
  const clear = () => { setFiles([]); setPreview(null); };
  const onDrop = (e) => { e.preventDefault(); setOver(false); load([...e.dataTransfer.files]); };

  return (
    <>
      <Title eyebrow="Work / Intake" title="Intake">
        Upload an email with its whole thread and attachments, paste a request, or run one of the walkthrough requests. The Intake agent reads everything and hands the key values to the other agents.
      </Title>
      <section className="card" aria-label="How to run">
        <div className="row" style={{ alignItems: 'center', justifyContent: 'space-between' }}>
          <div className="stack" style={{ gap: 4 }}><h2>How should the agents run?</h2>
            <p className="small muted">{mode === 'auto' ? 'All agents run straight through; you watch them light up one by one.' : 'The request stops after each agent. You review what it did, then run the next one.'}</p></div>
          <div className="seg" role="radiogroup" aria-label="Run mode">
            <button type="button" role="radio" aria-checked={mode === 'auto'} className={mode === 'auto' ? 'on' : ''} onClick={() => setMode('auto')}>Auto run</button>
            <button type="button" role="radio" aria-checked={mode === 'step'} className={mode === 'step' ? 'on' : ''} onClick={() => setMode('step')}>Agent by agent</button>
          </div>
        </div>
      </section>
      <Err error={error} />
      {busy && <div className="notice info" role="status">{busy}…{busy.startsWith('Reading the upload') ? '' : ' the agents are working. This takes a few seconds with Claude.'}</div>}

      <section className="card">
        <h2>Upload an email</h2>
        <p className="small muted">Saved email (.eml or Outlook .msg) plus any extra documents (.pdf, .docx, .txt). The thread inside the email is read as a whole.</p>
        <div className={'drop' + (over ? ' over' : '')} onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={onDrop}>
          <p style={{ marginBottom: 10 }}>Drop files here, or</p>
          <label className="btn" style={{ position: 'relative' }}>Choose files
            <input type="file" multiple accept=".eml,.msg,.pdf,.docx,.txt,.md" style={{ position: 'absolute', opacity: 0, width: 1, height: 1 }}
              onChange={(e) => { load([...e.target.files]); e.target.value = ''; }} />
          </label>
        </div>
        {files.length > 0 && (
          <div className="row" style={{ alignItems: 'center' }}>
            <span className="small">{files.map((f) => f.name).join(' · ')}</span>
            <button type="button" className="btn" onClick={clear}>Remove</button>
            {preview && <button type="button" className="btn dark" disabled={!!busy} onClick={() => run('Reading the email', () => api.post(`/uploads/${preview.id}/submit?mode=${mode}`))}>Submit to agents</button>}
          </div>
        )}
        {preview && <EmailPreview mail={preview} />}
      </section>

      <section className="card">
        <h2>Paste a request</h2>
        <label className="lbl" htmlFor="paste">Email text or form contents</label>
        <textarea id="paste" rows={6} value={text} onChange={(e) => setText(e.target.value)} placeholder="Hi, we'd like to open an account for…" />
        <button type="button" className="btn dark" style={{ alignSelf: 'flex-start' }} disabled={!text.trim() || !!busy} onClick={() => run('Reading the request', () => api.post('/requests/text', { text, mode }))}>Submit to agents</button>
      </section>

      <section className="card">
        <h2>Walkthrough requests</h2>
        <p className="small muted">Three sample emails with attachments that cover a new customer, a customer that already exists, and an existing site with a new owner.</p>
        <div className="row">
          {(sc.data || []).map((s) => (
            <div key={s.key} className="card" style={{ flex: '1 1 260px' }}>
              <span className="small muted">{s.title}</span>
              <h3>{s.party}</h3>
              <span className="small">{s.subject}</span>
              <span className="small muted">Attachments: {s.attachments.join(', ')}</span>
              <button type="button" className="btn dark" style={{ alignSelf: 'flex-start' }} disabled={!!busy} onClick={() => run('Running ' + s.party, () => api.post(`/scenarios/${s.key}/run?mode=${mode}`))}>Run through the agents</button>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
