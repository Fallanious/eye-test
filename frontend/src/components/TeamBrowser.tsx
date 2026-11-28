import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { positiveId, useBrowseParams } from '../hooks/useBrowseParams';
import { fetchTeams, fetchTeamGames, fetchGameClips, gameClipUrl, type GameScope } from '../api';
import type { BrowserTeam, TeamGame, GameClip, GameClipPage } from '../types';
import { TEAM_ALIASES, cardColors, teamName, teamColors } from '../teamTheme';
import GamePlayerFilter from './GamePlayerFilter';
import ClipStack from './ClipStack';
import TeamPickerPreview from './TeamPickerPreview';
import LoadingCrossfade from './LoadingCrossfade';
import GameLoadingRows from './GameLoadingRows';
import { GAME_FILTERS, PLAY_LABELS, playLabel } from '../playLabels';

function message(error: unknown) { return error instanceof Error ? error.message : 'Could not load film.'; }
function dateLabel(date: string) { return new Date(`${date}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }); }
type FilmGame = Pick<TeamGame, 'id' | 'date' | 'season' | 'home' | 'away'>;
type FilmTeam = Pick<BrowserTeam, 'id' | 'abbr' | 'name'>;
function matchupLabel(game: FilmGame, team: FilmTeam) { return game.home === team.abbr ? `vs ${teamName(game.away)}` : `at ${teamName(game.home)}`; }
function periodLabel(period: number) { return period <= 4 ? `Q${period}` : period === 5 ? 'OT' : `${period - 4}OT`; }

// White and pale team colors need darkening when used as small text on paper.
function teamStyle(team: FilmTeam): CSSProperties { return cardColors(team.abbr); }

export default function TeamBrowser() {
  const [teams, setTeams] = useState<BrowserTeam[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const { teamId, gameId } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    const controller = new AbortController();
    fetchTeams(controller.signal).then(data => { setTeams(data.teams); setError(''); })
      .catch(err => { if (!controller.signal.aborted) setError(message(err)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [attempt]);

  const team = teams.find(item => item.id === positiveId(teamId));

  if (loading && gameId) return <GameLoadingRows matchup count={1} />;
  if (!loading && error) return <div role="alert" className="notice">{error} <button onClick={() => { setLoading(true); setAttempt(a => a + 1); }}>Retry</button></div>;
  if (!loading && teamId && !team) return <p className="empty">Team not found.</p>;
  if (!loading && !teams.length) return <p className="empty">No team film is available yet.</p>;
  const games = team && <TeamGames key={team.id} team={team} />;
  if (gameId) return games;

  return <section aria-label="Team film library">
    <header className="tb-heading"><div><h1>Teams</h1><p>Choose a team to see its games and watch clips.</p></div></header>
    <div className="tb-layout">
      <LoadingCrossfade ready={!loading} preview={<TeamPickerPreview />}>
        <div className="tb-team-picker" role="group" aria-label="Choose a team">
          {teams.map(item => <button key={item.id} className="pb-team-tab pb-card" style={teamStyle(item)}
            aria-label={teamName(item.abbr)} title={teamName(item.abbr)} aria-pressed={item.id === team?.id}
            onClick={() => navigate(`/teams/${item.id}`)}>
            <span className="pb-card-layer" aria-hidden="true" />
            <span className="pb-info">{TEAM_ALIASES[item.abbr] || item.abbr}</span>
          </button>)}
        </div>
      </LoadingCrossfade>
      {games}
    </div>
  </section>;
}

function TeamGames({ team }: { team: BrowserTeam }) {
  const { gameId } = useParams();
  const navigate = useNavigate();
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

  if (gameId) {
    const game = games.find(item => item.id === positiveId(gameId));
    if (game) return <GameFilm key={game.id} team={team} game={game} />;
    return <><Link className="pb-back" to={`/teams/${team.id}`}>All {team.abbr} games</Link>
      {error ? <p role="alert">{error}</p> : <p role="status">{loading ? 'Loading game…' : 'Game not found for this team.'}</p>}</>;
  }

  return <section className="tb-games" aria-label={`${teamName(team.abbr)} games`}>
    <div className="tb-games-heading"><div className="tb-team-title"><ClipStack className="pb-team-mark" colors={teamColors(team.abbr)} /><h2>{teamName(team.abbr)}</h2></div><span>{team.games} games with film</span></div>
    {error && <div role="alert" className="notice">{error} <button onClick={() => { setError(''); setLoading(true); setAttempt(a => a + 1); }}>Retry</button></div>}
    <div className="tb-game-list">
      {games.map(game => <button className="tb-game-card" key={game.id} onClick={() => navigate(`/teams/${team.id}/games/${game.id}`)}>
        <span className="tb-game-identity"><span><strong>{matchupLabel(game, team)}</strong><small>{dateLabel(game.date)} · {game.home === team.abbr ? 'Home' : 'Away'} · {game.season}</small></span></span>
        <span className="tb-game-count">{game.team_clips} team clips<small>{game.clips} in game</small></span>
      </button>)}
      {loading && <GameLoadingRows />}
    </div>
    {!loading && !error && !games.length && <p className="empty">No games with clips for this team.</p>}
  </section>;
}

export function GameMatchupTitle({ away, home }: { away: string; home: string }) {
  return <h1 className="tb-matchup-title">
    <span className="games-team"><ClipStack className="pb-team-mark" colors={teamColors(away)} />{teamName(away)}</span>
    <span>at</span>
    <span className="games-team"><ClipStack className="pb-team-mark" colors={teamColors(home)} />{teamName(home)}</span>
  </h1>;
}

export function GameFilm({ team, game, scope = 'team', back }: { team: FilmTeam; game: FilmGame; scope?: GameScope; back?: string }) {
  const { params, update } = useBrowseParams();
  const clutch = params.get('clutch') === '1';
  const categoryValues = params.getAll('category').join(',');
  const playerValues = params.getAll('player').join(',');
  const categories = useMemo(() => categoryValues.split(',').filter(value => GAME_FILTERS.some(item => item.category === value)), [categoryValues]);
  const players = useMemo(() => playerValues.split(',').map(positiveId).filter(id => id !== null), [playerValues]);
  const activeId = positiveId(params.get('clip'));
  const [active, setActive] = useState<GameClip | null>(null);
  const [playAttempt, setPlayAttempt] = useState(0);
  function play(clip: GameClip) {
    setActive(clip);
    setPlayAttempt(n => n + 1);
    update({ clip: String(clip.id) });
  }
  return <section className="tb-film-page" style={teamStyle(team)} aria-label="Game film">
    <Link className="pb-back" to={back ?? `/teams/${team.id}`}>{back ? 'Games' : `All ${team.abbr} games`}</Link>
    <div className="tb-heading">
      {scope === 'both' ? <GameMatchupTitle away={game.away} home={game.home} /> : <div className="tb-team-title">
        <ClipStack className="pb-team-mark" colors={teamColors(team.abbr)} />
        <h1>{matchupLabel(game, team)}</h1>
      </div>}
      <p>{dateLabel(game.date)} · {game.season}</p>
    </div>
    <div className="tb-scope"><span>{scope === 'both' ? 'Both teams' : teamName(team.abbr)} plays</span><span>{categories.length > 1 ? 'Matches any selected category' : 'Filter this game by category'}</span></div>
    <GamePlayerFilter scope={scope} team={team} gameId={game.id} selected={players} onChange={ids => update({ player: ids.map(String) })} />
    <div className="pb-types tb-categories"><button className={!categories.length ? 'active' : ''} aria-pressed={!categories.length} onClick={() => update({ category: [] })}>{PLAY_LABELS.all}</button>
      <button aria-pressed={clutch} className={clutch ? 'active' : ''} onClick={() => update({ clutch: clutch ? '' : '1' })}>Clutch</button>
      {GAME_FILTERS.map(({ category: key, label }) => <button key={key} className={categories.includes(key) ? 'active' : ''} aria-pressed={categories.includes(key)} onClick={() => update({ category: categories.includes(key) ? categories.filter(c => c !== key) : [...categories, key] })}>{label}</button>)}
    </div>
    <div className="pb-session tb-film-session">
      <section className="tb-preview" aria-label="Clip preview">
        {activeId ? <GamePreview scope={scope} key={`${activeId}:${playAttempt}`} team={team} game={game} clipId={activeId} selected={active?.id === activeId ? active : null} onClear={() => update({ clip: '' })} />
          : <div className="tb-video-stage"><div className="pb-placeholder">Select a play to watch</div></div>}
      </section>
      <GameClipList scope={scope} key={JSON.stringify([categories, clutch, players])} players={players} clutch={clutch} team={team} game={game} categories={categories} active={activeId} onPlay={play} />
    </div>
  </section>;
}

function GamePreview({ scope, team, game, clipId, selected, onClear }: {
  scope: GameScope; team: FilmTeam; game: FilmGame; clipId: number; selected: GameClip | null; onClear: () => void;
}) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const [details, setDetails] = useState(selected);
  useEffect(() => {
    if (selected) return;
    const controller = new AbortController();
    fetchGameClips(team.id, game.id, [], false, [], null, controller.signal, clipId, scope)
      .then(page => { if (!controller.signal.aborted) setDetails(page.clips[0] ?? null); })
      .catch(() => {});
    return () => controller.abort();
  }, [team.id, game.id, clipId, selected, scope]);
  return <>
    <div className="tb-video-stage">
      <video controls playsInline autoPlay src={gameClipUrl(team.id, game.id, clipId)} onLoadedData={() => setLoaded(true)} onError={() => setFailed(true)} />
      {!loaded && !failed && <span className="tb-video-loading pb-loading-fade" role="status">Loading play…</span>}
    </div>
    {failed && <p className="notice" role="alert">Could not load this clip. Select it again to retry. <button onClick={onClear}>Clear preview</button></p>}
    {details && <div className="pb-now"><h2>{details.description}</h2><p>{periodLabel(details.period)} · {details.game_clock} · {details.duration_label}</p></div>}
  </>;
}

function GameClipList({ scope, team, game, players, categories, clutch, active, onPlay }: { scope: GameScope; team: FilmTeam; game: FilmGame; players: number[]; categories: string[]; clutch: boolean; active: number | null; onPlay: (clip: GameClip) => void }) {
  const [page, setPage] = useState<GameClipPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const alive = useRef(true);
  const busy = useRef(false);
  useEffect(() => {
    alive.current = true;
    const controller = new AbortController();
    fetchGameClips(team.id, game.id, categories, clutch, players, null, controller.signal, undefined, scope)
      .then(data => { setPage(data); setError(''); })
      .catch(err => { if (!controller.signal.aborted) setError(message(err)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => { alive.current = false; controller.abort(); };
  }, [team.id, game.id, categories, clutch, players, attempt, scope]);
  async function more() {
    if (!page?.cursor || busy.current) return;
    busy.current = true; setLoading(true); setError('');
    try { const data = await fetchGameClips(team.id, game.id, categories, clutch, players, page.cursor, undefined, undefined, scope); if (alive.current) setPage(prev => ({ ...data, clips: [...(prev?.clips ?? []), ...data.clips] })); }
    catch (err) { if (alive.current) setError(message(err)); }
    finally { busy.current = false; if (alive.current) setLoading(false); }
  }
  return <section className="pb-plays tb-clip-panel" aria-label="Game plays"><div className="pb-queue-head"><div className="pb-plays-head"><h2>Plays</h2><span role="status">{page ? `${page.total} clips` : 'Loading plays…'}</span></div></div>
    <div className="pb-queue-scroll">
      {error && <div role="alert" className="notice">{error} {!page && <button onClick={() => { setLoading(true); setAttempt(a => a + 1); }}>Retry</button>}</div>}
      {page?.clips.map(clip => <button key={clip.id} className={`pb-row ${active === clip.id ? 'current' : ''}`} aria-pressed={active === clip.id} onClick={() => onPlay(clip)}><span><strong>{clip.description}</strong><small>{periodLabel(clip.period)} · {clip.game_clock}</small></span><span className="pb-kind">{clip.categories.map(playLabel).join(' · ')}</span><span className="pb-duration">{clip.duration_label}</span></button>)}
      {loading && <div className="tb-loading pb-loading-fade" role="status">Loading plays…</div>}
      {!loading && page?.clips.length === 0 && <p className="empty">No plays match these filters.</p>}
      {page?.cursor && <button className="tb-more" disabled={loading} onClick={() => void more()}>Load more plays</button>}
    </div>
  </section>;
}
