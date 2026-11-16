import PlayerBrowser from './components/PlayerBrowser';
import ClipStack from './components/ClipStack';

export default function App() {
  return <div className="app-shell">
    <header className="app-header">
      <a className="brand" href="/" aria-label="EYE TEST home">
        <ClipStack className="brand-mark" />
        <span className="brand-wordmark" aria-hidden="true"><span>EYE</span><span>TEST</span></span>
      </a>
      <span className="app-section">Library</span>
    </header>
    <main><PlayerBrowser /></main>
    <footer className="app-disclaimer">
      EYE TEST is an independent project and is not affiliated with, endorsed by, or sponsored by the NBA or any NBA team.
    </footer>
  </div>;
}
