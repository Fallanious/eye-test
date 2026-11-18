import { useState } from 'react';
import TeamBrowser from './components/TeamBrowser';
import PlayerBrowser from './components/PlayerBrowser';
import ClipStack from './components/ClipStack';

export default function App() {
  const [tab, setTab] = useState<'players' | 'teams'>('players');
  return <div className="app-shell">
    <header className="app-header">
      <a className="brand" href="/" aria-label="EYE TEST home">
        <ClipStack className="brand-mark" />
        <span className="brand-wordmark" aria-hidden="true"><span>EYE</span><span>TEST</span></span>
      </a>
      <nav className="app-tabs" aria-label="Browse film">
        <button className={`app-section ${tab === 'players' ? 'active' : ''}`} aria-current={tab === 'players' ? 'page' : undefined} onClick={() => setTab('players')}>Library</button>
        <button className={`app-section ${tab === 'teams' ? 'active' : ''}`} aria-current={tab === 'teams' ? 'page' : undefined} onClick={() => setTab('teams')}>Teams</button>
      </nav>
    </header>
    <main>{tab === 'players' ? <PlayerBrowser /> : <TeamBrowser />}</main>
    <footer className="app-disclaimer">
      EYE TEST is an independent project and is not affiliated with, endorsed by, or sponsored by the NBA or any NBA team.
    </footer>
  </div>;
}
