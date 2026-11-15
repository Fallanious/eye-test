import PlayerBrowser from './components/PlayerBrowser';

export default function App() {
  return <div className="app-shell">
    <aside className="sidebar"><a className="brand" href="/">EYE TEST<span>THE PLAYER FILM ROOM</span></a></aside>
    <main><PlayerBrowser /></main>
  </div>;
}
