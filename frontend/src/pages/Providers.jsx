import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import { Title, useLoad, Err } from '../components.jsx';

const AUTH = [
  ['none', 'None'], ['api_key_header', 'API key in a header'], ['api_key_query', 'API key in the query string'],
  ['bearer', 'Bearer token'], ['oauth_client_credentials', 'OAuth 2.0 client credentials'], ['certificate', 'Client certificate (mutual TLS)'],
];
const SECRET_FIELDS = { api_key_header: [['apiKey', 'API key']], api_key_query: [['apiKey', 'API key']], bearer: [['token', 'Token']],
  oauth_client_credentials: [['clientId', 'Client ID'], ['clientSecret', 'Client secret']], certificate: [], none: [] };

export default function Providers() {
  const d = useLoad(() => api.get('/providers'), []);
  const [sel, setSel] = useState('dnb');
  const [form, setForm] = useState(null);
  const [secrets, setSecrets] = useState({});
  const [mapping, setMapping] = useState('');
  const [msg, setMsg] = useState(null);
  const [disc, setDisc] = useState('');
  const [testing, setTesting] = useState(false);
  const list = (d.data && d.data.providers) || [];
  const cur = list.find((p) => p.key === sel);
  useEffect(() => { if (cur) { setForm({ ...cur.config }); setMapping(JSON.stringify(cur.config.mapping || {}, null, 2)); setSecrets({}); setMsg(null); } }, [sel, d.data]); // eslint-disable-line
  useEffect(() => { if (d.data) setDisc(d.data.settings.disclaimer); }, [d.data]);

  const save = async (extra = {}) => {
    let map;
    try { map = JSON.parse(mapping || '{}'); } catch { setMsg({ err: true, t: 'Field mapping is not valid JSON.' }); return; }
    try {
      await api.put('/providers/' + sel, { config: { ...form, mapping: map, ...extra }, secrets });
      setMsg({ t: 'Saved.' }); setSecrets({}); d.reload();
    } catch (e) { setMsg({ err: true, t: e.message }); }
  };
  const setMode = async (live) => { await api.put('/providers/' + sel, { config: { mode: live ? 'live' : 'test' }, secrets: {} }); d.reload(); };
  const test = async () => { setTesting(true); try { const r = await api.post(`/providers/${sel}/test`); setMsg({ err: !r.ok, t: `Test connection: ${r.ok ? 'reachable' : 'failed'} · ${r.message} · ${r.ms} ms` }); d.reload(); } finally { setTesting(false); } };
  const saveDisc = async () => { await api.put('/provider-settings', { disclaimer: disc }); d.reload(); setMsg({ t: 'Disclaimer saved.' }); };
  const f = (k) => (form && form[k] != null ? form[k] : '');
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <>
      <Title eyebrow="Platform / Third-party data" title="Third-party data">
        Configure the providers the agents call. Each provider runs on test data until you switch it to its live API, so you can replace them one at a time.
      </Title>
      <Err error={d.error} />
      <section className="card">
        <h2>Disclaimer shown on requests that used test data</h2>
        <label className="lbl" htmlFor="disc">Wording</label>
        <textarea id="disc" rows={2} value={disc} onChange={(e) => setDisc(e.target.value)} />
        <button type="button" className="btn" style={{ alignSelf: 'flex-start' }} onClick={saveDisc}>Save disclaimer</button>
      </section>
      <div className="row">
        <div className="side stack" style={{ maxWidth: 320, gap: 8 }}>
          {list.map((p) => (
            <button type="button" key={p.key} className={'list-item' + (p.key === sel ? ' on' : '')} onClick={() => setSel(p.key)}>
              <span className="row" style={{ justifyContent: 'space-between', width: '100%', alignItems: 'center' }}><strong>{p.name}</strong><span className={'pmode ' + p.config.mode}>{p.config.mode === 'live' ? 'Live API' : 'Test data'}</span></span>
              <span className="small muted">{p.purpose}</span>
              <span className="small muted">Used by: {p.agent}</span>
            </button>
          ))}
        </div>
        {cur && form && (
          <article className="card grow">
            <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
              <div><h2>{cur.name}</h2><span className="small muted">{cur.purpose} · used by the {cur.agent} agent</span></div>
              <label className="toggle"><input type="checkbox" checked={cur.config.mode === 'live'} onChange={(e) => setMode(e.target.checked)} /><span className="tr" aria-hidden="true" />{cur.config.mode === 'live' ? 'Live API' : 'Test data'}</label>
            </div>
            {cur.config.mode === 'live' && !cur.config.baseUrl && <div className="notice warn small">Live is on but no base URL is set, so this provider returns no result and the agent sends the request to a steward.</div>}
            {msg && <div className={'notice small ' + (msg.err ? 'err' : 'info')} role="status">{msg.t}</div>}
            <h3>Connection</h3>
            <div className="form">
              <div className="f"><label className="lbl" htmlFor="pu">Base URL</label><input id="pu" type="text" value={f('baseUrl')} onChange={set('baseUrl')} placeholder="https://api.provider.com" /></div>
              <div className="f"><label className="lbl" htmlFor="pm">Method</label><select id="pm" value={f('method') || 'GET'} onChange={set('method')}><option>GET</option><option>POST</option></select></div>
              <div className="f" style={{ gridColumn: '1 / -1' }}><label className="lbl" htmlFor="pp">Endpoint path</label><input id="pp" type="text" value={f('path')} onChange={set('path')} />
                <span className="small muted">Placeholders: {'{name} {street} {city} {address} {tin} {dea} {license}'}</span></div>
              <div className="f"><label className="lbl" htmlFor="pt">Timeout (ms)</label><input id="pt" type="text" value={f('timeoutMs')} onChange={set('timeoutMs')} /></div>
              <div className="f"><label className="lbl" htmlFor="pr">Retries</label><input id="pr" type="text" value={f('retries')} onChange={set('retries')} /></div>
            </div>
            <h3>Authentication</h3>
            <div className="form">
              <div className="f"><label className="lbl" htmlFor="pa">Type</label><select id="pa" value={f('authType') || 'none'} onChange={set('authType')}>{AUTH.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></div>
              {f('authType') === 'api_key_header' && <div className="f"><label className="lbl" htmlFor="ph">Header name</label><input id="ph" type="text" value={f('headerName')} onChange={set('headerName')} /></div>}
              {f('authType') === 'api_key_query' && <div className="f"><label className="lbl" htmlFor="pq">Query parameter</label><input id="pq" type="text" value={f('queryName')} onChange={set('queryName')} /></div>}
              {f('authType') === 'oauth_client_credentials' && <>
                <div className="f"><label className="lbl" htmlFor="ptu">Token URL</label><input id="ptu" type="text" value={f('tokenUrl')} onChange={set('tokenUrl')} /></div>
                <div className="f"><label className="lbl" htmlFor="ps">Scope (optional)</label><input id="ps" type="text" value={f('scope')} onChange={set('scope')} /></div></>}
              {(SECRET_FIELDS[f('authType')] || []).map(([k, l]) => (
                <div className="f" key={k}><label className="lbl" htmlFor={'sec-' + k}>{l}</label>
                  <input id={'sec-' + k} type="password" autoComplete="off" value={secrets[k] || ''} onChange={(e) => setSecrets({ ...secrets, [k]: e.target.value })} placeholder={cur.secrets[k] ? `Saved ${cur.secrets[k]} · type to replace` : 'Not set'} /></div>
              ))}
              {f('authType') === 'certificate' && <p className="small muted">Client certificates are not supported yet in this workbench.</p>}
            </div>
            <p className="small muted">Secrets are stored on this computer in backend/secrets.local.json (owner-only, not in git) and are never shown again. In production they belong in a vault such as Azure Key Vault.</p>
            <h3>Field mapping</h3>
            <p className="small muted">Map the provider's response to the fields the agents use: {cur.fields.join(', ')}. Use dotted paths, e.g. "matchCandidates.0.organization.duns". Starting values are a guide; confirm them against the provider's documentation.</p>
            <textarea rows={7} className="mono" value={mapping} onChange={(e) => setMapping(e.target.value)} aria-label="Field mapping (JSON)" />
            <div className="row" style={{ gap: 8 }}>
              <button type="button" className="btn dark" onClick={() => save()}>Save</button>
              <button type="button" className="btn" disabled={testing} onClick={test}>{testing ? 'Testing…' : 'Test connection'}</button>
              {cur.config.lastTest && <span className="small muted" style={{ alignSelf: 'center' }}>Last test {cur.config.lastTest.at}: {cur.config.lastTest.ok ? 'reachable' : 'failed'} ({cur.config.lastTest.message})</span>}
            </div>
          </article>
        )}
      </div>
    </>
  );
}
