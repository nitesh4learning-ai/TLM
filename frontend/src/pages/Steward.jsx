import React from 'react';
import { api } from '../api.js';
import { Title, PolicyChip, useLoad, Err } from '../components.jsx';

export default function Steward() {
  const q = useLoad(() => api.get('/queue'), []);
  return (
    <>
      <Title eyebrow="Work / Steward queue" title="Steward queue">Stages where a policy says a person decides, or no policy applies. Open one to see the detail and approve it.</Title>
      <Err error={q.error} />
      <section className="card">
        {q.data && q.data.length === 0 && <p className="muted">Nothing waiting.</p>}
        {q.data && q.data.length > 0 && (
          <div className="scroll"><table><thead><tr><th>Request</th><th>Party</th><th>Stage</th><th>Waiting for</th><th>Why</th><th>Policies</th></tr></thead>
            <tbody>{q.data.map((x, i) => (
              <tr key={i}><td><a className="mono" href={`#/journey/${x.requestId}`}>{x.requestId}</a></td><td>{x.legalName}</td><td>{x.stageName}</td>
                <td><span className="tag human">{x.waitingFor}</span></td><td>{x.summary}</td><td>{x.policies.map((p) => <PolicyChip key={p} id={p} />)}</td></tr>
            ))}</tbody></table></div>
        )}
      </section>
    </>
  );
}
