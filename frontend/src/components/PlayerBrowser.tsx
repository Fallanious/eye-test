import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { usePlayerClip } from '../hooks/usePlayerClip';
import { usePlayerClips } from '../hooks/usePlayerClips';
import { usePlayerLibrary } from '../hooks/usePlayerLibrary';
import type { BrowserPlayer } from '../types';
import ClipStack from './ClipStack';

// Away Game palettes, ordered from the nearest layer to the furthest.
const NBA_COLORS: Record<string, readonly [string, string, string]> = {
  PHI: ['#006BB6', '#ED174C', '#FFFFFF'],
  BOS: ['#007A33', '#BA9653', '#FFFFFF'],
  NYK: ['#006BB6', '#F58426', '#BEC0C2'],
  BKN: ['#000000', '#FFFFFF', '#707271'],
  TOR: ['#CE1141', '#000000', '#A1A1A4'],
  CHI: ['#CE1141', '#000000', '#FFFFFF'],
  CLE: ['#860038', '#BC945C', '#000000'],
  DET: ['#C8102E', '#1D42BA', '#BEC0C2'],
  IND: ['#002D62', '#FDBB30', '#BEC0C2'],
  MIL: ['#00471B', '#EEE1C6', '#0077C0'],
  ATL: ['#C8102E', '#FDB927', '#000000'],
  CHA: ['#1D1160', '#00788C', '#A1A1A4'],
  MIA: ['#98002E', '#F9A01B', '#000000'],
  ORL: ['#0077C0', '#C4CED4', '#000000'],
  WAS: ['#002B5C', '#E31837', '#C4CED4'],
  DAL: ['#00538C', '#002B5E', '#B8C4CA'],
  DEN: ['#0E2240', '#FEC524', '#8B2131'],
  GSW: ['#1D428A', '#FFC72C', '#FFFFFF'],
  HOU: ['#CE1141', '#000000', '#C4CED4'],
  LAC: ['#041E42', '#C8102E', '#0072CE'],
  LAL: ['#552583', '#FDB927', '#000000'],
  MEM: ['#5D76A9', '#12173F', '#F5B112'],
  MIN: ['#236192', '#00843D', '#FFFFFF'],
  NOP: ['#0C2340', '#C8102E', '#85714D'],
  OKC: ['#007AC1', '#EF3B24', '#FDBB30'],
  PHX: ['#1D1160', '#E56020', '#000000'],
  POR: ['#E03A3E', '#000000', '#FFFFFF'],
  SAC: ['#5A2D81', '#000000', '#63727A'],
  SAS: ['#C4CED4', '#000000', '#FFFFFF'],
  UTA: ['#6C4C9A', '#69B3E7', '#121212'],
};

const TEAM_ALIASES: Record<string, string> = { BRK: 'BKN', CHO: 'CHA', PHO: 'PHX' };

const TEAM_NAMES: Record<string, string> = {
  ATL: 'Atlanta Hawks', BOS: 'Boston Celtics', BKN: 'Brooklyn Nets',
  CHA: 'Charlotte Hornets', CHI: 'Chicago Bulls', CLE: 'Cleveland Cavaliers',
  DAL: 'Dallas Mavericks', DEN: 'Denver Nuggets', DET: 'Detroit Pistons',
  GSW: 'Golden State Warriors', HOU: 'Houston Rockets', IND: 'Indiana Pacers',
  LAC: 'LA Clippers', LAL: 'Los Angeles Lakers', MEM: 'Memphis Grizzlies',
  MIA: 'Miami Heat', MIL: 'Milwaukee Bucks', MIN: 'Minnesota Timberwolves',
  NOP: 'New Orleans Pelicans', NYK: 'New York Knicks', OKC: 'Oklahoma City Thunder',
  ORL: 'Orlando Magic', PHI: 'Philadelphia 76ers', PHX: 'Phoenix Suns',
  POR: 'Portland Trail Blazers', SAC: 'Sacramento Kings', SAS: 'San Antonio Spurs',
  TOR: 'Toronto Raptors', UTA: 'Utah Jazz', WAS: 'Washington Wizards',
};

function teamName(team: string) {
  return TEAM_NAMES[TEAM_ALIASES[team] || team] || team;
}

function teamColors(team: string): readonly [string, string, string] {
  return NBA_COLORS[TEAM_ALIASES[team] || team] || ['#242426', '#A68168', '#D8CEC5'];
}

function cardColors(team: string): CSSProperties {
  const [primary, middle, back] = teamColors(team);
  return {
    '--card-primary': primary,
    '--card-middle': middle,
    '--card-back': back,
  } as CSSProperties;
}

function countLabel(count: number, one: string, many: string) {
  return `${count} ${count === 1 ? one : many}`;
}

function PlayerSkeleton({ index }: { index: number }) {
  return (
    <div className="pb-card pb-skeleton-card" style={{ '--shimmer-delay': `${(index % 3) * 0.16}s` } as CSSProperties}>
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
  const library = usePlayerLibrary();
  const clips = usePlayerClips();
  const film = usePlayerClip();
  const [broken, setBroken] = useState<Record<number, boolean>>({});
  const queueRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLLIElement>(null);
  const playersEndRef = useRef<HTMLDivElement>(null);
  const selected = clips.selected;
  const playerColor = selected?.team ? teamColors(selected.team)[0] : '#242426';
  const archive = library.season ? `${library.season} archive` : '';
  const markBroken = (id: number) => setBroken(prev => ({ ...prev, [id]: true }));
  const filters = [{ role: '', label: 'All plays' }, ...clips.roles];

  const { hasMore: moreClips, loadMore: loadMoreClips } = clips;
  const { hasMore: morePlayers, loadMore: loadMorePlayers } = library;

  useEffect(() => {
    const node = endRef.current;
    if (!node || !moreClips) return;
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) void loadMoreClips();
    }, { root: queueRef.current });
    observer.observe(node);
    return () => observer.disconnect();
  }, [moreClips, clips.clips.length, loadMoreClips, selected]);

  useEffect(() => {
    const node = playersEndRef.current;
    if (!node || !morePlayers || selected) return;
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) void loadMorePlayers();
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [morePlayers, library.players.length, loadMorePlayers, selected]);

  return (
    <>
      {selected ? (
        <>
          <button className="pb-back" onClick={() => { film.clear(); clips.close(); }}>Back</button>
          <div className="pb-card pb-selected" style={cardColors(selected.team)} aria-label={`${selected.full_name} selected player`}>
            <span className="pb-card-layer" aria-hidden="true" />
            <PlayerCard player={selected} broken={!!broken[selected.id]} onBroken={() => markBroken(selected.id)} />
          </div>
          <div className="pb-session" style={{ '--player-color': playerColor } as CSSProperties}>
            <section className="pb-preview" aria-label="Film preview">
              <div className="pb-stage" aria-busy={film.cutting}>
                {film.url ? <video key={film.url} className="main-player pb-film" controls autoPlay playsInline preload="auto" src={film.url} onLoadedData={film.started} onError={film.failed} /> :
                  <div className={`pb-placeholder ${film.cutting ? 'pb-shimmer' : ''}`} role="status">
                    {film.cutting ? 'Loading this play…' : film.error ? 'Preview unavailable' : selected.clips === 0 ? 'No clips available for this player yet.' : 'Select a play to watch'}
                  </div>}
              </div>
              {film.error && <p role="alert" className="notice">{film.error}</p>}

            </section>
            <section className="pb-plays" aria-label="Player plays">
              <div className="pb-queue-head">
                <div className="pb-plays-head">
                  <h2>Plays</h2>
                  <span role="status">{clips.loading ? 'Loading plays…' : !clips.role ? countLabel(selected.clips, 'clip', 'clips') : ''}</span>
                </div>
                <div className="pb-types">
                  {filters.map(item => (
                    <button key={item.label} aria-pressed={clips.role === item.role} className={clips.role === item.role ? 'active' : ''} onClick={() => { clips.chooseRole(item.role); if (queueRef.current) queueRef.current.scrollTop = 0; }}>{item.label}</button>
                  ))}
                </div>
              </div>
              <div className="pb-queue-scroll" ref={queueRef}>
                {clips.error && <p role="alert" className="notice">{clips.error}</p>}
                <ul className="pb-list">
                  {clips.loading && !clips.shown.length && Array.from({ length: 5 }, (_, index) => (
                    <li key={`loading-${index}`} aria-hidden="true">
                      <div className="pb-row pb-skeleton-row" style={{ '--shimmer-delay': `${index * 0.12}s` } as CSSProperties}>
                        <div>
                          <div className="pb-skeleton pb-skeleton-line" />
                          <div className="pb-skeleton pb-skeleton-line short" />
                        </div>
                        <div className="pb-skeleton pb-skeleton-line pb-kind" />
                        <div className="pb-skeleton pb-skeleton-line" />
                      </div>
                    </li>
                  ))}
                  {clips.shown.map(clip => (
                    <li key={`${clip.id}-${clip.role}`}>
                      <button
                        className={`pb-row ${film.active?.id === clip.id && film.active.role === clip.role ? 'current' : ''}`}
                        aria-pressed={film.active?.id === clip.id && film.active.role === clip.role}
                        onClick={() => film.play(selected.id, clip)}
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
                      <div className="pb-row pb-skeleton-row" style={{ '--shimmer-delay': `${index * 0.12}s` } as CSSProperties}>
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
                {!clips.loading && !clips.loadingMore && !clips.shown.length && <p className="empty">{selected.clips === 0 ? 'No clips available for this player yet.' : 'No plays in this group.'}</p>}
              </div>
            </section>
          </div>
        </>
      ) : (
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
            <input aria-label="Search players" placeholder="Search players…" value={library.query} onChange={event => library.setQuery(event.target.value)} />
          </div>
          <div className="pb-team-tabs" role="group" aria-label="Browse by team">
            <button className="pb-team-tab pb-card" style={cardColors('')} aria-pressed={!library.team} onClick={() => library.setTeam('')}>
              <span className="pb-card-layer" aria-hidden="true" />
              <span className="pb-info">All</span>
            </button>
            {library.teams.map(code => (
              <button key={code} className="pb-team-tab pb-card" style={cardColors(code)} aria-pressed={library.team === code} aria-label={teamName(code)} title={teamName(code)} onClick={() => library.setTeam(code)}>
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
                <button className="pb-card" style={cardColors(player.team)} key={player.id} onClick={() => { window.scrollTo({ top: 0 }); void clips.open(player); }}>
                  <span className="pb-card-layer" aria-hidden="true" />
                  <PlayerCard
                    player={player}
                    broken={!!broken[player.id]}
                    onBroken={() => markBroken(player.id)}
                  />
                </button>
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
      )}
    </>
  );
}
