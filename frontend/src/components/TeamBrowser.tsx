import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { fetchTeams, fetchTeamGames, fetchGameClips, gameClipUrl } from '../api';
import type { BrowserTeam, TeamGame, GameClip, GameClipPage } from '../types';
import { TEAM_ALIASES, cardColors, teamName, teamColors } from '../teamTheme';
import GamePlayerFilter from './GamePlayerFilter';
import ClipStack from './ClipStack';
import { GAME_FILTERS, PLAY_LABELS, playLabel } from '../playLabels';

function message(error: unknown) { return error instanceof Error ? error.message : 'Could not load film.'; }
function dateLabel(date: string) { return new Date(`${date}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }); }
function matchupLabel(game: TeamGame, team: BrowserTeam) { return game.home === team.abbr ? `vs ${teamName(game.away)}` : `at ${teamName(game.home)}`; }
function periodLabel(period: number) { return period <= 4 ? `Q${period}` : period === 5 ? 'OT' : `${period - 4}OT`; }

// White and pale team colors need darkening when used as small text on paper.
function teamStyle(team: BrowserTeam): CSSProperties { return cardColors(team.abbr); }

export default function TeamBrowser() {
  const [teams, setTeams] = useState<BrowserTeam[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [game, setGame] = useState<TeamGame | null>(null);


  useEffect(() => {
    const controller = new AbortController();
    fetchTeams(controller.signal).then(data => { setTeams(data.teams); setError(''); })
      .catch(err => { if (!controller.signal.aborted) setError(message(err)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [attempt]);

  const team = teams.find(item => item.id === selected) ?? teams[0];

  if (loading) return <div className="tb-loading pb-loading-fade" role="status">Loading teams…</div>;
  if (error) return <div role="alert" className="notice">{error} <button onClick={() => { setLoading(true); setAttempt(a => a + 1); }}>Retry</button></div>;
  if (!team) return <p className="empty">No team film is available yet.</p>;
  if (game) return <GameFilm key={`${team.id}:${game.id}`} team={team} game={game} onBack={() => setGame(null)} />;


  return <section aria-label="Team film library">
    <header className="tb-heading"><div><h1>Teams</h1><p>Pick a team, a game, and browse clips.</p></div></header>
    <div className="tb-layout">
      <div className="tb-team-picker" role="group" aria-label="Choose a team">
        {teams.map(item => <button key={item.id} className="pb-team-tab pb-card" style={teamStyle(item)}
          aria-label={teamName(item.abbr)} title={teamName(item.abbr)} aria-pressed={item.id === team.id}
          onClick={() => setSelected(item.id)}>
          <span className="pb-card-layer" aria-hidden="true" />
          <span className="pb-info">{TEAM_ALIASES[item.abbr] || item.abbr}</span>
        </button>)}
      </div>
      <TeamGames key={team.id} team={team} onSelect={setGame} />
    </div>
  </section>;
}

function TeamGames({ team, onSelect }: { team: BrowserTeam; onSelect: (game: TeamGame) => void }) {
  const [games, setGames] = useState<TeamGame[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    async function loadGames() {
      let cursor: number | null = null;
      const loaded: TeamGame[] = [];
      do {
        const page = await fetchTeamGames(team.id, cursor, controller.signal);
        if (controller.signal.aborted) return;
        loaded.push(...page.games);
        setGames([...loaded]);
        cursor = page.cursor;
      } while (cursor != null);
    }
    loadGames().catch(err => {
      if (!controller.signal.aborted) setError(message(err));
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [team.id, attempt]);

  return <section className="tb-games" aria-label={`${teamName(team.abbr)} games`}>
    <div className="tb-games-heading"><div className="tb-team-title"><ClipStack className="pb-team-mark" colors={teamColors(team.abbr)} /><h2>{teamName(team.abbr)}</h2></div><span>{team.games} games with film</span></div>
    {error && <div role="alert" className="notice">{error} <button onClick={() => { setError(''); setLoading(true); setAttempt(a => a + 1); }}>Retry</button></div>}
    <div className="tb-game-list">
      {games.map(game => <button className="tb-game-card" key={game.id} onClick={() => onSelect(game)}>
        <span className="tb-game-identity"><span><strong>{matchupLabel(game, team)}</strong><small>{dateLabel(game.date)} · {game.home === team.abbr ? 'Home' : 'Away'} · {game.season}</small></span></span>
        <span className="tb-game-count">{game.team_clips} team clips<small>{game.clips} in game</small></span>
      </button>)}
      {loading && Array.from({ length: 3 }, (_, i) => <div key={i} className="tb-game-card tb-game-skeleton" aria-hidden="true"><span className="pb-skeleton pb-skeleton-line" /><span className="pb-skeleton pb-skeleton-line short" /></div>)}
    </div>
    {!loading && !error && !games.length && <p className="empty">No games with clips for this team.</p>}
  </section>;
}


function GameFilm({ team, game, onBack }: { team: BrowserTeam; game: TeamGame; onBack: () => void }) {
  const [players, setPlayers] = useState<number[]>([]);
  const [clutch, setClutch] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);
  const [active, setActive] = useState<GameClip | null>(null);
  const [playAttempt, setPlayAttempt] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  function play(clip: GameClip) { setPlayAttempt(n => n + 1); setActive(clip); setLoading(true); setError(''); }
  return <section className="tb-film-page" style={teamStyle(team)} aria-label="Game film">
    <button className="pb-back" onClick={onBack}>All {team.abbr} games</button>
    <div className="tb-heading">
      <div className="tb-team-title">
        <ClipStack className="pb-team-mark" colors={teamColors(team.abbr)} />
        <h1>{matchupLabel(game, team)}</h1>
      </div>
      <p>{dateLabel(game.date)} · {game.season}</p>
    </div>
    <div className="tb-scope"><span>{teamName(team.abbr)} plays</span><span>{categories.length > 1 ? 'Matches any selected category' : 'Filter this game by category'}</span></div>
    <GamePlayerFilter team={team} gameId={game.id} selected={players} onChange={setPlayers} />
    <div className="pb-types tb-categories"><button className={!categories.length ? 'active' : ''} aria-pressed={!categories.length} onClick={() => setCategories([])}>{PLAY_LABELS.all}</button>
      <button aria-pressed={clutch} className={clutch ? 'active' : ''} onClick={() => setClutch(!clutch)}>Clutch</button>
      {GAME_FILTERS.map(({ category: key, label }) => <button key={key} className={categories.includes(key) ? 'active' : ''} aria-pressed={categories.includes(key)} onClick={() => setCategories(prev => prev.includes(key) ? prev.filter(c => c !== key) : [...prev, key])}>{label}</button>)}
    </div>
    <div className="pb-session tb-film-session">
      <section className="tb-preview" aria-label="Clip preview">
        <div className="tb-video-stage">
          {active ? <video key={`${active.id}:${playAttempt}`} controls playsInline autoPlay src={gameClipUrl(team.id, game.id, active.id)} onLoadedData={() => setLoading(false)} onError={() => { setLoading(false); setError('Could not load this clip. Select it again to retry.'); }} /> : <div className="pb-placeholder">Select a play to watch</div>}
          {loading && <span className="tb-video-loading pb-loading-fade" role="status">Loading play…</span>}
        </div>
        {error && <p className="notice" role="alert">{error} <button onClick={() => setActive(null)}>Clear preview</button></p>}
        {active && <div className="pb-now"><h2>{active.description}</h2><p>{periodLabel(active.period)} · {active.game_clock} · {active.duration_label}</p></div>}
      </section>
      <GameClipList key={JSON.stringify([categories, clutch, players])} players={players} clutch={clutch} team={team} game={game} categories={categories} active={active} onPlay={play} />
    </div>
  </section>;
}

function GameClipList({ team, game, players, categories, clutch, active, onPlay }: { team: BrowserTeam; game: TeamGame; players: number[]; categories: string[]; clutch: boolean; active: GameClip | null; onPlay: (clip: GameClip) => void }) {
  const [page, setPage] = useState<GameClipPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const alive = useRef(true);
  const busy = useRef(false);
  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    fetchGameClips(team.id, game.id, categories, clutch, players, null, controller.signal)
      .then(data => { setPage(data); setError(''); })
      .catch(err => { if (!controller.signal.aborted) setError(message(err)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => { alive.current = false; controller.abort(); };
  }, [team.id, game.id, categories, clutch, players, attempt]);
  async function more() {
    if (!page?.cursor || busy.current) return;
    busy.current = true; setLoading(true); setError('');
    try { const data = await fetchGameClips(team.id, game.id, categories, clutch, players, page.cursor); if (alive.current) setPage(prev => ({ ...data, clips: [...(prev?.clips ?? []), ...data.clips] })); }
    catch (err) { if (alive.current) setError(message(err)); }
    finally { busy.current = false; if (alive.current) setLoading(false); }
  }
  return <section className="pb-plays tb-clip-panel" aria-label="Game plays"><div className="pb-queue-head"><div className="pb-plays-head"><h2>Plays</h2><span role="status">{page ? `${page.total} clips` : 'Loading plays…'}</span></div></div>
    <div className="pb-queue-scroll">
      {error && <div role="alert" className="notice">{error} {!page && <button onClick={() => { setLoading(true); setAttempt(a => a + 1); }}>Retry</button>}</div>}
      {page?.clips.map(clip => <button key={clip.id} className={`pb-row ${active?.id === clip.id ? 'current' : ''}`} aria-pressed={active?.id === clip.id} onClick={() => onPlay(clip)}><span><strong>{clip.description}</strong><small>{periodLabel(clip.period)} · {clip.game_clock}</small></span><span className="pb-kind">{clip.categories.map(playLabel).join(' · ')}</span><span className="pb-duration">{clip.duration_label}</span></button>)}
      {loading && <div className="tb-loading pb-loading-fade" role="status">Loading plays…</div>}
      {!loading && page?.clips.length === 0 && <p className="empty">No plays match these filters.</p>}
      {page?.cursor && <button className="tb-more" disabled={loading} onClick={() => void more()}>Load more plays</button>}
    </div>
  </section>;
}
