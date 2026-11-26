import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { Link, useParams } from 'react-router';
import { fetchPlayer, playerClipUrl } from '../api';
import { positiveId, useBrowseParams } from '../hooks/useBrowseParams';
import { usePlayerClips } from '../hooks/usePlayerClips';
import { usePlayerLibrary } from '../hooks/usePlayerLibrary';
import type { BrowserPlayer } from '../types';
import ClipStack from './ClipStack';

import { teamName, teamColors, cardColors, TEAM_ALIASES } from '../teamTheme';

import { PLAYER_FILTERS } from '../playLabels';

function countLabel(count: number, one: string, many: string) {
  return `${count} ${count === 1 ? one : many}`;
}

function PlayerSkeleton({ index }: { index: number }) {
  return (
    <div className="pb-card pb-skeleton-card" style={{ '--loading-delay': `${(index % 3) * 0.16}s` } as CSSProperties}>
      <div className="pb-info">
        <div className="pb-portrait pb-skeleton" />
        <div className="pb-copy">
          <div className="pb-skeleton pb-skeleton-line" />
          <div className="pb-skeleton pb-skeleton-line" />
          <div className="pb-skeleton pb-skeleton-line" />
        </div>
      </div>
    </div>
  );
}

function PlayerCard({ player, broken, onBroken }: {
  player: BrowserPlayer;
  broken: boolean;
  onBroken: () => void;
}) {
  const color = player.team ? teamColors(player.team)[0] : undefined;
  return (
    <div className="pb-info" style={{ '--player-color': color || '#242426' } as CSSProperties}>
      <div className="pb-portrait">
        {(!player.headshot_url || broken) && <span className="pb-initials">{player.full_name.split(' ').slice(0, 2).map(name => name[0]).join('')}</span>}
        {player.headshot_url && !broken && (
          <img src={player.headshot_url} alt="" referrerPolicy="no-referrer" onError={onBroken} />
        )}
      </div>
      <div className="pb-copy">
        {player.team && <span className="pb-abbr" style={{ color }}>{player.team}</span>}
        <strong>{player.full_name}</strong>
        <div className="pb-meta">{[player.position, countLabel(player.games, 'game', 'games')].filter(Boolean).join(' · ')}</div>
        <div className="pb-bottom">
          <span>{countLabel(player.clips, 'clip', 'clips')}</span>
        </div>
      </div>
    </div>
  );
}

export default function PlayerBrowser() {
  const { playerId } = useParams();
  if (playerId === undefined) return <PlayerLibrary />;
  const id = positiveId(playerId);
  return id ? <PlayerDetail key={id} id={id} /> : <p role="alert">Player not found.</p>;
}

function PlayerLibrary() {
  const { params, update } = useBrowseParams();
  const library = usePlayerLibrary(params.get('q') || '', params.get('team') || '');
  const archive = library.season ? `${library.season} archive` : '';
  const playersEndRef = useRef<HTMLDivElement>(null);
  const [broken, setBroken] = useState<Record<number, boolean>>({});
  const markBroken = (id: number) => setBroken(prev => ({ ...prev, [id]: true }));

  const { hasMore: morePlayers, loadMore: loadMorePlayers } = library;
  useEffect(() => {
    const node = playersEndRef.current;
    if (!node || !morePlayers) return;
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) void loadMorePlayers();
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [morePlayers, library.players.length, loadMorePlayers]);

  return (
    <>
      <header className="pb-head">
        <div>

          <div className="pb-title">
            <h1>Player Library</h1>
            {archive && <span>{archive}</span>}
          </div>
          <p>Browse clips by player.</p>
        </div>
      </header>
      <div className="toolbar pb-toolbar">
        <input aria-label="Search players" placeholder="Search players…" value={library.query} onChange={event => update({ q: event.target.value }, true)} />
      </div>
      <div className="pb-team-tabs" role="group" aria-label="Browse by team">
        <button className="pb-team-tab pb-card" style={cardColors('')} aria-pressed={!library.team} onClick={() => update({ team: '' })}>
          <span className="pb-card-layer" aria-hidden="true" />
          <span className="pb-info">All</span>
        </button>
        {library.teams.map(code => (
          <button key={code} className="pb-team-tab pb-card" style={cardColors(code)} aria-pressed={library.team === code} aria-label={teamName(code)} title={teamName(code)} onClick={() => update({ team: code })}>
            <span className="pb-card-layer" aria-hidden="true" />
            <span className="pb-info">{TEAM_ALIASES[code] || code}</span>
          </button>
        ))}
      </div>
      {library.team && <div className="pb-team-heading">
        <ClipStack className="pb-team-mark" colors={teamColors(library.team)} />
        <h2>{teamName(library.team)}</h2>
        <span className="pb-team-rule" />
        <span role="status">{library.loading ? 'Loading…' : countLabel(library.total, 'player', 'players')}</span>
      </div>}
      {library.error && <p role="alert" className="notice">{library.error}</p>}
      {library.loading && !library.players.length ? (
        <div className="pb-grid" aria-hidden="true">
          {Array.from({ length: 6 }, (_, index) => <PlayerSkeleton key={index} index={index} />)}
        </div>
      ) : (
        <div className="pb-grid">
          {library.players.map(player => (
            <Link className="pb-card" style={cardColors(player.team)} key={player.id} to={{ pathname: `/players/${player.id}`, search: params.toString() }} onClick={() => window.scrollTo({ top: 0 })}>
              <span className="pb-card-layer" aria-hidden="true" />
              <PlayerCard
                player={player}
                broken={!!broken[player.id]}
                onBroken={() => markBroken(player.id)}
              />
            </Link>
          ))}
        </div>
      )}
      {library.loadingMore && (
        <div className="pb-grid" aria-hidden="true">
          {Array.from({ length: 3 }, (_, index) => <PlayerSkeleton key={index} index={index} />)}
        </div>
      )}
      {library.hasMore && <div ref={playersEndRef} className="pb-more" aria-hidden="true" />}
      {!library.loading && !library.loadingMore && !library.players.length && <p className="empty">{library.query || library.team ? 'No players match your search.' : 'No players available yet.'}</p>}
    </>
  );
}

function PlayerDetail({ id }: { id: number }) {
  const { params, update } = useBrowseParams();
  const role = PLAYER_FILTERS.find(item => item.role === params.get('role'))?.role || '';
  const clutch = params.get('clutch') === '1';
  const clipId = positiveId(params.get('clip'));
  const clipRole = params.get('clipRole');
  const [attempt, setAttempt] = useState(0);
  const [selected, setSelected] = useState<BrowserPlayer | null>(null);
  const [error, setError] = useState('');
  const clips = usePlayerClips(id, role, clutch);
  const queueRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLLIElement>(null);
  const [broken, setBroken] = useState<Record<number, boolean>>({});
  const markBroken = (id: number) => setBroken(prev => ({ ...prev, [id]: true }));

  const { hasMore: moreClips, loadMore: loadMoreClips } = clips;
  useEffect(() => {
    const controller = new AbortController();
    fetchPlayer(id, controller.signal).then(player => {
      if (!controller.signal.aborted) setSelected(player);
    }).catch(err => { if (!controller.signal.aborted) setError(err.message); });
    return () => controller.abort();
  }, [id]);

  useEffect(() => {
    const node = endRef.current;
    if (!node || !moreClips) return;
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) void loadMoreClips();
    }, { root: queueRef.current });
    observer.observe(node);
    return () => observer.disconnect();
  }, [moreClips, clips.clips.length, loadMoreClips, selected]);

  const listParams = new URLSearchParams();
  for (const key of ['team', 'q']) {
    const value = params.get(key);
    if (value) listParams.set(key, value);
  }
  const back = <Link className="pb-back" to={{ pathname: '/players', search: listParams.toString() }}>Back</Link>;
  if (!selected) return <>{back}{error ? <p role="alert">{error}</p> : <p role="status">Loading player…</p>}</>;
  const playerColor = selected.team ? teamColors(selected.team)[0] : '#242426';
  return (
    <>
      {back}
      <div className="pb-card pb-selected" style={cardColors(selected.team)} aria-label={`${selected.full_name} selected player`}>
        <span className="pb-card-layer" aria-hidden="true" />
        <PlayerCard player={selected} broken={!!broken[selected.id]} onBroken={() => markBroken(selected.id)} />
      </div>
      <div className="pb-types tb-categories" role="group" aria-label="Filter player plays by category">
        <button aria-pressed={clutch} className={clutch ? 'active' : ''} onClick={() => update({ clutch: clutch ? '' : '1' })}>Clutch</button>
        {PLAYER_FILTERS.map(item => (
          <button key={item.label} aria-pressed={role === item.role} className={role === item.role ? 'active' : ''} onClick={() => { update({ role: item.role }); if (queueRef.current) queueRef.current.scrollTop = 0; }}>{item.label}</button>
        ))}
      </div>
      <div className="pb-session" style={{ '--player-color': playerColor } as CSSProperties}>
        <section className="pb-preview" aria-label="Film preview">
          <PlayerPreview key={clipId} player={selected} clipId={clipId} attempt={attempt} />
        </section>
        <section className="pb-plays" aria-label="Player plays">
          <div className="pb-queue-head">
            <div className="pb-plays-head">
              <h2>Plays</h2>
              <span role="status">{clips.loading ? 'Loading plays…' : !role && !clutch ? countLabel(selected.clips, 'clip', 'clips') : ''}</span>
            </div>
          </div>
          <div className="pb-queue-scroll" ref={queueRef}>
            {clips.error && <p role="alert" className="notice">{clips.error}</p>}
            <ul className="pb-list">
              {clips.loading && !clips.clips.length && Array.from({ length: 5 }, (_, index) => (
                <li key={`loading-${index}`} aria-hidden="true">
                  <div className="pb-row pb-skeleton-row" style={{ '--loading-delay': `${index * 0.12}s` } as CSSProperties}>
                    <div>
                      <div className="pb-skeleton pb-skeleton-line" />
                      <div className="pb-skeleton pb-skeleton-line short" />
                    </div>
                    <div className="pb-skeleton pb-skeleton-line pb-kind" />
                    <div className="pb-skeleton pb-skeleton-line" />
                  </div>
                </li>
              ))}
              {clips.clips.map(clip => (
                <li key={`${clip.id}-${clip.role}`}>
                  <button
                    className={`pb-row ${clipId === clip.id && (!clipRole || clipRole === clip.role) ? 'current' : ''}`}
                    aria-pressed={clipId === clip.id && (!clipRole || clipRole === clip.role)}
                    onClick={() => { setAttempt(n => n + 1); update({ clip: String(clip.id), clipRole: clip.role }); }}
                  >
                    <span>
                      <strong>{clip.description}</strong>
                      <small>{clip.matchup} · Q{clip.period} · {clip.game_clock}</small>
                    </span>
                    <span className="pb-kind">{clip.role_label}</span>
                    <span className="pb-duration">{clip.duration_label}</span>
                  </button>
                </li>
              ))}
              {clips.loadingMore && Array.from({ length: 2 }, (_, index) => (
                <li key={`more-${index}`} aria-hidden="true">
                  <div className="pb-row pb-skeleton-row" style={{ '--loading-delay': `${index * 0.12}s` } as CSSProperties}>
                    <div>
                      <div className="pb-skeleton pb-skeleton-line" />
                      <div className="pb-skeleton pb-skeleton-line short" />
                    </div>
                    <div className="pb-skeleton pb-skeleton-line pb-kind" />
                    <div className="pb-skeleton pb-skeleton-line" />
                  </div>
                </li>
              ))}
              {clips.hasMore && <li ref={endRef} className="pb-more" aria-hidden="true" />}
            </ul>
            {!clips.loading && !clips.loadingMore && !clips.clips.length && <p className="empty">{selected.clips === 0 ? 'No clips available for this player yet.' : 'No plays in this group.'}</p>}
          </div>
        </section>
      </div>
    </>
  );
}

function PlayerPreview({ player, clipId, attempt }: { player: BrowserPlayer; clipId: number | null; attempt: number }) {
  const [failedAttempt, setFailedAttempt] = useState<number | null>(null);
  const [loaded, setLoaded] = useState(false);
  const failed = failedAttempt === attempt;
  return <>
    <div className="pb-stage" aria-busy={!!clipId && !loaded && !failed}>
      {clipId && !failed
        ? <video className="main-player pb-film" controls autoPlay playsInline preload="auto" src={playerClipUrl(player.id, clipId)} onLoadedData={() => setLoaded(true)} onError={() => setFailedAttempt(attempt)} />
        : <div className="pb-placeholder" role="status">{failed ? 'Preview unavailable' : player.clips === 0 ? 'No clips available for this player yet.' : 'Select a play to watch'}</div>}
    </div>
    {failed && <p role="alert" className="notice">Could not cut this clip.</p>}
  </>;
}
