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
      <span className="app-tagline">Basketball, on film.</span>
    </header>
    <main><PlayerBrowser /></main>
  </div>;
}
