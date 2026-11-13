import React, { useState } from 'react';
import { api, go } from '../api.js';
import { Title, useLoad, Err } from '../components.jsx';

export default function Intake() {
  const sc = useLoad(() => api.get('/scenarios'), []);
  const [files, setFiles] = useState([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState(null);
  const [over, setOver] = useState(false);

  const run = async (label, fn) => {
    setBusy(label); setError(null);
    try { const r = await fn(); go('journey/' + r.id); } catch (e) { setError(e.message); } finally { setBusy(''); }
  };
  const onDrop = (e) => { e.preventDefault(); setOver(false); setFiles([...files, ...e.dataTransfer.files]); };

  return (
    <>
      <Title eyebrow="Work / Intake" title="Intake">
        Upload an email with its whole thread and attachments, paste a request, or run one of the walkthrough requests. The Intake agent reads everything and hands the key values to the other agents.
      </Title>
      <Err error={error} />
      {busy && <div className="notice info" role="status">{busy}… the agents are working. This takes a few seconds with Claude.</div>}

      <section className="card">
        <h2>Upload an email</h2>
        <p className="small muted">Saved email (.eml or Outlook .msg) plus any extra documents (.pdf, .docx, .txt). The thread inside the email is read as a whole.</p>
        <div className={'drop' + (over ? ' over' : '')} onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={onDrop}>
          <p style={{ marginBottom: 10 }}>Drop files here, or</p>
          <label className="btn" style={{ position: 'relative' }}>Choose files
            <input type="file" multiple accept=".eml,.msg,.pdf,.docx,.txt,.md" style={{ position: 'absolute', opacity: 0, width: 1, height: 1 }}
              onChange={(e) => setFiles([...files, ...e.target.files])} />
          </label>
        </div>
        {files.length > 0 && (
          <div className="row" style={{ alignItems: 'center' }}>
            <span className="small">{files.map((f) => f.name).join(' · ')}</span>
            <button type="button" className="btn" onClick={() => setFiles([])}>Clear</button>
            <button type="button" className="btn dark" disabled={!!busy} onClick={() => run('Reading the email', () => api.upload('/requests/upload', files))}>Submit to agents</button>
          </div>
        )}
      </section>

      <section className="card">
        <h2>Paste a request</h2>
        <label className="lbl" htmlFor="paste">Email text or form contents</label>
        <textarea id="paste" rows={6} value={text} onChange={(e) => setText(e.target.value)} placeholder="Hi, we'd like to open an account for…" />
        <button type="button" className="btn dark" style={{ alignSelf: 'flex-start' }} disabled={!text.trim() || !!busy} onClick={() => run('Reading the request', () => api.post('/requests/text', { text }))}>Submit to agents</button>
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
              <button type="button" className="btn dark" style={{ alignSelf: 'flex-start' }} disabled={!!busy} onClick={() => run('Running ' + s.party, () => api.post(`/scenarios/${s.key}/run`))}>Run through the agents</button>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
