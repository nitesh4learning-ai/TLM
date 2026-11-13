import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
import { api } from './api.js';
import ControlTower from './pages/ControlTower.jsx';
import Intake from './pages/Intake.jsx';
import Journey from './pages/Journey.jsx';
import Steward from './pages/Steward.jsx';
import Records from './pages/Records.jsx';
import Hierarchy from './pages/Hierarchy.jsx';
import Agents from './pages/Agents.jsx';
import Policies from './pages/Policies.jsx';
import Providers from './pages/Providers.jsx';

const NAV = [
  ['tower', 'Control tower'], ['h', 'Work'], ['intake', 'Intake'], ['steward', 'Steward queue'],
  ['h', 'Records'], ['journey', 'Request journey'], ['records', 'Business ready records'], ['hierarchy', 'Hierarchies'],
  ['h', 'Platform'], ['agents', 'Agents'], ['policies', 'Policy studio'], ['providers', 'Third-party data'],
];

function useRoute() {
  const parse = () => (window.location.hash.replace(/^#\/?/, '') || 'tower').split('/');
  const [r, setR] = useState(parse());
  useEffect(() => { const f = () => setR(parse()); window.addEventListener('hashchange', f); return () => window.removeEventListener('hashchange', f); }, []);
  return r;
}

function App() {
  const [page, ...rest] = useRoute();
  const arg = rest.join('/');
  const [health, setHealth] = useState(null);
  const [queue, setQueue] = useState(0);
  useEffect(() => {
    api.get('/health').then(setHealth).catch(() => setHealth({ ok: false }));
    const t = () => api.get('/queue').then((q) => setQueue(q.length)).catch(() => {});
    t(); const i = setInterval(t, 5000); return () => clearInterval(i);
  }, []);
  const P = { tower: ControlTower, intake: Intake, journey: Journey, steward: Steward, records: Records, hierarchy: Hierarchy, agents: Agents, policies: Policies, providers: Providers }[page] || ControlTower;
  return (
    <div className="shell">
      <header className="top">
        <a className="brand" href="#/tower"><span className="logo" aria-hidden="true">✦</span>Agentic MDM</a>
        <span className="pill">{health === null ? 'Connecting…' : !health.ok ? 'API not reachable on port 8000' : health.llm ? `Claude connected · ${health.model}` : 'Claude not configured: add ANTHROPIC_API_KEY to backend/.env'}</span>
      </header>
      <div className="body">
        <nav className="nav" aria-label="Main">
          {NAV.map(([k, label], i) => k === 'h' ? <div key={i} className="head">{label}</div> : (
            <a key={k} href={'#/' + k} className={page === k ? 'on' : ''} aria-current={page === k ? 'page' : undefined}>
              <span>{label}</span>{k === 'steward' && queue > 0 && <span className="badge">{queue}</span>}
            </a>
          ))}
        </nav>
        <main><P arg={arg} /></main>
      </div>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
