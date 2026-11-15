import PlayerBrowser from './components/PlayerBrowser';

export default function App() {
  return <div className="app-shell">
    <header className="app-header"><a className="brand" href="/">EYE TEST</a><span className="app-section">Players</span><span className="app-tagline">THE PLAYER FILM ROOM</span></header>
    <main><PlayerBrowser /></main>
  </div>;
}
