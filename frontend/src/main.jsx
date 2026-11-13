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

/** Four applications, one per layer, sharing one sign-in and one look. Control tower sits above them. */
const APPS = [
  { key: 'overview', name: 'Control tower', who: 'Overview', accent: '#131820', pages: [['tower', 'Control tower']] },
  { key: 'work', name: 'Work', who: 'People: intake, stewardship, approvals', accent: '#B45309', pages: [['intake', 'Intake'], ['steward', 'Steward queue']] },
  { key: 'agents', name: 'Agent console', who: 'Agents: runs, roster, data providers', accent: '#1D47B8', pages: [['journey', 'Request journey'], ['agents', 'Agents'], ['providers', 'Third-party data']] },
  { key: 'policy', name: 'Policy studio', who: 'Governance: policies for agents and people', accent: '#6D3FC0', pages: [['policies', 'Policies']] },
  { key: 'records', name: 'Records', who: 'Hub: Business ready records, read-only', accent: '#0E7C66', pages: [['records', 'Business ready records'], ['hierarchy', 'Hierarchies']] },
];
const PAGES = { tower: ControlTower, intake: Intake, journey: Journey, steward: Steward, records: Records, hierarchy: Hierarchy, agents: Agents, policies: Policies, providers: Providers };

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
  const app = APPS.find((a) => a.pages.some(([k]) => k === page)) || APPS[0];
  const P = PAGES[page] || ControlTower;
  return (
    <div className="shell">
      <header className="top">
        <a className="brand" href="#/tower"><span className="logo" aria-hidden="true">✦</span>Agentic MDM</a>
        <nav className="apps" aria-label="Applications">
          {APPS.map((a) => (
            <a key={a.key} href={'#/' + a.pages[0][0]} className={'appsw' + (a.key === app.key ? ' on' : '')} aria-current={a.key === app.key ? 'true' : undefined} style={{ '--acc': a.accent }}>
              <span className="dot" aria-hidden="true" />{a.name}{a.key === 'work' && queue > 0 && <span className="badge">{queue}</span>}
            </a>
          ))}
        </nav>
        <span className="pill" style={{ marginLeft: 'auto' }}>{health === null ? 'Connecting…' : !health.ok ? 'API not reachable on port 8000' : health.llm ? `Claude connected · ${health.model}` : 'Claude not configured'}</span>
      </header>
      <div className="body">
        {app.key !== 'overview' && (
          <nav className="nav" aria-label={app.name} style={{ '--acc': app.accent }}>
            <div className="appname"><span className="dot" aria-hidden="true" />{app.name}</div>
            <div className="small muted" style={{ padding: '0 12px 10px' }}>{app.who}</div>
            {app.pages.map(([k, label]) => (
              <a key={k} href={'#/' + k} className={page === k ? 'on' : ''} aria-current={page === k ? 'page' : undefined}>
                <span>{label}</span>{k === 'steward' && queue > 0 && <span className="badge">{queue}</span>}
              </a>
            ))}
          </nav>
        )}
        <main><P arg={arg} /></main>
      </div>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
