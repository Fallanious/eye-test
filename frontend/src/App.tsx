import { Link, Navigate, NavLink, Route, Routes } from 'react-router';
import TeamBrowser from './components/TeamBrowser';
import PlayerBrowser from './components/PlayerBrowser';
import ClipStack from './components/ClipStack';

export default function App() {
  return <div className="app-shell">
    <header className="app-header">
      <Link className="brand" to="/players" aria-label="EYE TEST home">
        <ClipStack className="brand-mark" />
        <span className="brand-wordmark" aria-hidden="true"><span>EYE</span><span>TEST</span></span>
      </Link>
      <nav className="app-tabs" aria-label="Browse film">
        <NavLink className="app-section" to="/players">Library</NavLink>
        <NavLink className="app-section" to="/teams">Teams</NavLink>
      </nav>
    </header>
    <main>
      <Routes>
        <Route path="/" element={<Navigate to="/players" replace />} />
        <Route path="/players/:playerId?" element={<PlayerBrowser />} />
        <Route path="/teams/:teamId?" element={<TeamBrowser />} />
        <Route path="/teams/:teamId/games/:gameId" element={<TeamBrowser />} />
      </Routes>
    </main>
    <footer className="app-disclaimer">
      EYE TEST is an independent project and is not affiliated with, endorsed by, or sponsored by the NBA or any NBA team.
    </footer>
  </div>;
}
