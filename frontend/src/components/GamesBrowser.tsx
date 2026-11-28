import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';
import { fetchClipDates, fetchSchedule } from '../api';
import type { ScheduledGame } from '../types';
import { teamColors, teamName } from '../teamTheme';
import ClipStack from './ClipStack';
import { GameFilm } from './TeamBrowser';

const DAY = 86400000;
const WEEK = 7 * DAY;
const BUFFER_WEEKS = 52;
const MONTHS = Array.from({ length: 12 }, (_, month) =>
  format(Date.UTC(2000, month, 1), { month: 'long' }));
function iso(time: number) { return new Date(time).toISOString().slice(0, 10); }
function parse(value: string | null | undefined) {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const time = Date.parse(value);
  return Number.isFinite(time) && iso(time) === value ? time : null;
}
function monday(time: number) { return time - ((new Date(time).getUTCDay() + 6) % 7) * DAY; }
function format(time: number, options: Intl.DateTimeFormatOptions) {
  return new Date(time).toLocaleDateString('en-US', { ...options, timeZone: 'UTC' });
}
function today() {
  return new Intl.DateTimeFormat('sv-SE', { timeZone: 'America/New_York' }).format(new Date());
}

function WeekStrip({ selected, initialWeek, onSelect, onWeek }: {
  selected: number; initialWeek: number; onSelect: (day: number) => void; onWeek: (week: number) => void;
}) {
  const rail = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(initialWeek);
  const [center, setCenter] = useState(initialWeek);
  const first = center - BUFFER_WEEKS * WEEK;
  const weeks = useMemo(() => Array.from({ length: 2 * BUFFER_WEEKS + 1 }, (_, i) => first + i * WEEK), [first]);
  const visibleRef = useRef(visible);
  const weekEnd = new Date(visible + 6 * DAY);
  const month = weekEnd.getUTCMonth();
  const year = weekEnd.getUTCFullYear();

  const [availability, setAvailability] = useState<{ year: number; dates: Set<string> } | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    fetchClipDates(year, controller.signal).then(({ dates }) => {
      if (!controller.signal.aborted) {
        setAvailability({ year, dates: new Set(dates) });
      }
    }).catch(() => { /* The schedule remains usable without date markers. */ });
    return () => controller.abort();
  }, [year]);

  function show(week: number) {
    if (week === visibleRef.current) return;
    visibleRef.current = week;
    setVisible(week);
    onWeek(week);
    // Keep a stable scroll origin through month and year changes. Rebuild the
    // rail only at its outer weeks or when the picker jumps outside its range.
    if (Math.abs(week - center) >= BUFFER_WEEKS * WEEK) setCenter(week);
  }

  useLayoutEffect(() => {
    const node = rail.current!;
    let width = node.clientWidth;
    function align() { node.scrollLeft = (visibleRef.current - first) / WEEK * width; }
    align();
    const observer = new ResizeObserver(() => {
      if (node.clientWidth !== width) {
        width = node.clientWidth;
        align();
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [first]);

  function jump(week: number) {
    show(week);
    if (Math.abs(week - center) < BUFFER_WEEKS * WEEK) {
      const node = rail.current!;
      node.scrollLeft = (week - first) / WEEK * node.clientWidth;
    }
  }
  return <>
    <div className="games-toolbar"><h1>Games</h1><div className="games-paging">
      <select aria-label="Month" value={month}
        onChange={e => jump(monday(Date.UTC(year, Number(e.target.value), 1)))}>
        {MONTHS.map((name, index) => <option key={name} value={index}>{name}</option>)}
      </select>
      <select aria-label="Year" value={year}
        onChange={e => jump(monday(Date.UTC(Number(e.target.value), month, 1)))}>
        {Array.from({ length: 21 }, (_, index) => year - 10 + index).map(option =>
          <option key={option} value={option}>{option}</option>)}
      </select>
    </div></div>
    <div className="games-week-nav">
      <button aria-label="Previous week" onClick={() => jump(visible - 7 * DAY)}>‹</button>
      <div key={center} className="games-rail" ref={rail} aria-label="Weeks" onScroll={e => {
        const node = e.currentTarget;
        if (node === rail.current && node.clientWidth) {
          const index = Math.max(0, Math.min(weeks.length - 1, Math.round(node.scrollLeft / node.clientWidth)));
          show(weeks[index]);
        }
      }}>
        {weeks.map(week => <div className="games-week" key={week} inert={week !== visible}>
          {Math.abs(week - visible) <= 2 * 7 * DAY && Array.from({ length: 7 }, (_, i) => {
            const day = week + i * DAY;
            const hasClips = availability?.year === new Date(week + 6 * DAY).getUTCFullYear()
              ? availability.dates.has(iso(day)) : undefined;
            const clipLabel = hasClips === undefined ? '' : hasClips ? ', clips available' : ', no clips';
            return <button key={day} data-has-clips={hasClips} aria-label={format(day, { dateStyle: 'full' }) + clipLabel} aria-pressed={selected === day}
              onClick={() => onSelect(day)}><small>{format(day, { weekday: 'short' })}</small><strong>{new Date(day).getUTCDate()}</strong>
              <span className="games-clip-marker" data-available={hasClips} aria-hidden="true" />
            </button>;
          })}
        </div>)}
      </div>
      <button aria-label="Next week" onClick={() => jump(visible + 7 * DAY)}>›</button>
    </div>
    {availability?.year === year && <div className="games-strip-key">
      <span className="games-clip-marker" data-available="true" aria-hidden="true" /> Clips available
    </div>}
  </>;
}

function MatchupTeam({ team }: { team: string }) {
  return <span className="games-team">
    <ClipStack className="pb-team-mark" colors={teamColors(team)} />
    {teamName(team)}
  </span>;
}

function ClipStatus({ available }: { available: boolean }) {
  return <span className={'games-status' + (available ? ' available' : '')}>{available ? 'Clips available' : 'No clips'}</span>;
}
function status(game: ScheduledGame) {
  if (!game.start || !/\d{1,2}:\d{2}\s*[AP]M/i.test(game.status)) return game.status;
  return new Date(game.start).toLocaleTimeString('en-US', { timeZone: 'America/New_York', hour: 'numeric', minute: '2-digit' }) + ' ET';
}

export default function GamesBrowser() {
  const { day: routeDay, matchup } = useParams();
  const [params, setParams] = useSearchParams();
  const day = parse(routeDay ?? params.get('date')) ?? Date.parse(today());
  const date = iso(day);
  const week = monday(parse(params.get('week')) ?? day);
  const [result, setResult] = useState<{ date: string; games: ScheduledGame[]; incomplete: boolean } | null>(null);
  const [failure, setFailure] = useState<{ date: string; message: string } | null>(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    fetchSchedule(date, controller.signal).then(data => {
      if (!controller.signal.aborted) { setResult({ ...data, date }); setFailure(null); }
    }).catch((err: Error) => { if (!controller.signal.aborted) setFailure({ date, message: err.message }); });
    return () => controller.abort();
  }, [date, attempt]);
  const current = result?.date === date ? result : null;
  const retry = <button onClick={() => { setFailure(null); setAttempt(n => n + 1); }}>Retry</button>;
  const warning = current?.incomplete && <p role="status" className="notice">The full NBA schedule is unavailable. Showing catalog games. {retry}</p>;
  const loading = failure?.date === date ? <p role="alert" className="notice">{failure.message} {retry}</p>
    : !current ? <p role="status">Loading schedule…</p> : null;
  if (matchup) {
    const game = current?.games.find(g => g.away + '-at-' + g.home === matchup);
    const back = '/games?date=' + date + '&week=' + iso(week);
    if (game?.has_clips && game.id && game.home_id) return <GameFilm key={game.id} scope="both" back={back}
      team={{ id: game.home_id, abbr: game.home, name: teamName(game.home) }}
      game={{ ...game, id: game.id, date }} />;
    return <section><Link className="pb-back" to={back}>Games</Link>{loading || <>{warning}{game ? <>
      <h1>{teamName(game.away)} at {teamName(game.home)}</h1><p>{format(day, { dateStyle: 'full' })}{status(game) && ' · ' + status(game)}</p>
      <ClipStatus available={false} /></> : <p>Game unavailable for this date.</p>}</>}</section>;
  }
  return <section className="games-page">
    <WeekStrip selected={day} initialWeek={week} onWeek={value => setParams({ date, week: iso(value) }, { replace: true })}
      onSelect={value => setParams({ date: iso(value), week: iso(monday(value)) }, { replace: true })} />
    <h2 className="games-day-heading">{format(day, { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}</h2>
    {loading || <>{warning}{current?.games.map(game => {
      const label = status(game);
      const content = <>
        <span className="games-matchup-info">
          <strong className="games-opponents"><MatchupTeam team={game.away} /> <span className="games-at">at</span> <MatchupTeam team={game.home} /></strong>
          {label && <small>{label}</small>}
        </span>
        <ClipStatus available={game.has_clips} />
      </>;
      if (!game.has_clips) return <div key={game.key} className="tb-game-card games-matchup" data-has-clips="false">{content}</div>;
      return <Link key={game.key} className="tb-game-card games-matchup" data-has-clips="true"
        to={'/games/' + date + '/' + game.away + '-at-' + game.home + '?week=' + iso(week)}>{content}</Link>;
    })}{!current?.games.length && !current?.incomplete && <p>No games scheduled.</p>}</>}
  </section>;
}
