import { useEffect, useId, useRef, useState } from 'react';
import { fetchGamePlayers, type GamePlayer } from '../api';
import type { BrowserTeam } from '../types';

type Props = {
  team: BrowserTeam;
  gameId: number;
  selected: number[];
  onChange: (ids: number[]) => void;
};

function searchableName(value: string) {
  return value.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

export default function GamePlayerFilter({ team, gameId, selected, onChange }: Props) {
  const [roster, setRoster] = useState<GamePlayer[] | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const anchor = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  useEffect(() => {
    const controller = new AbortController();
    fetchGamePlayers(team.id, gameId, controller.signal)
      .then(data => { if (!controller.signal.aborted) setRoster(data.players); })
      .catch(err => { if (!controller.signal.aborted) setError(err.message || 'Could not load players.'); });
    return () => controller.abort();
  }, [team.id, gameId, attempt]);

  useEffect(() => {
    if (!open) return;
    function dismiss(event: PointerEvent | FocusEvent) {
      if (!anchor.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener('pointerdown', dismiss);
    document.addEventListener('focusin', dismiss);
    return () => {
      document.removeEventListener('pointerdown', dismiss);
      document.removeEventListener('focusin', dismiss);
    };
  }, [open]);

  function toggle(id: number) {
    onChange(selected.includes(id) ? selected.filter(value => value !== id) : [...selected, id]);
  }

  const query = searchableName(search.trim());
  const matches = roster?.filter(player => searchableName(player.full_name).includes(query));
  return <div className="tb-player-filters">
    <div className="tb-player-anchor" ref={anchor}
      onKeyDown={event => {
        if (event.key === 'Escape' && open) {
          setOpen(false);
          trigger.current?.focus();
        }
      }}>
      <button ref={trigger} aria-expanded={open} aria-controls={open ? panelId : undefined}
        onClick={() => { setSearch(''); setOpen(!open); }}>
        Players <span aria-hidden="true">{open ? '▴' : '▾'}</span>
      </button>
      {open && <section id={panelId} className="tb-player-menu" aria-label={team.name + ' players'}>
        <strong>{team.name} players</strong>
        <input autoFocus type="search" placeholder="Search players" aria-label="Search players"
          value={search} onChange={event => setSearch(event.target.value)} />
        {error ? <div role="alert">{error} <button onClick={() => { setError(''); setAttempt(n => n + 1); }}>Retry</button></div>
          : !matches ? <p role="status">Loading players…</p>
          : matches.length === 0 ? <p role="status">{roster?.length ? 'No matching players.' : 'No players linked to these plays.'}</p>
          : matches.map(player => <label key={player.id}>
            <input type="checkbox" checked={selected.includes(player.id)} onChange={() => toggle(player.id)} />
            {player.full_name}
          </label>)}
      </section>}
    </div>
    {roster?.filter(player => selected.includes(player.id)).map(player =>
      <button key={player.id} aria-label={'Remove ' + player.full_name} onClick={() => toggle(player.id)}>
        {player.full_name} <span aria-hidden="true">×</span>
      </button>)}
  </div>;
}
