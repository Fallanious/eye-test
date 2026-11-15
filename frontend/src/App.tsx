import PlayerBrowser from './components/PlayerBrowser';

export default function App() {
  return <div className="app-shell">
    <aside className="sidebar"><a className="brand" href="/">EYE TEST<span>THE PLAYER FILM ROOM</span></a><nav className="side-nav" aria-label="Library"><a className="nav-selected" href="/" aria-current="page">Players</a></nav></aside>
    <main><PlayerBrowser /></main>
  </div>;
}
