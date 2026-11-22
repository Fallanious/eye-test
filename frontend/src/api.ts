import type { PlayerLibrary, PlayerClipPage, TeamGame, BrowserTeam, GameClipPage } from "./types";
const BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '');
async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, init);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

export async function fetchPlayerLibrary(page?: { cursor?: number | null; team?: string; q?: string }): Promise<PlayerLibrary> {
  const params = new URLSearchParams();
  if (page?.cursor) params.set('cursor', String(page.cursor));
  if (page?.team) params.set('team', page.team);
  if (page?.q) params.set('q', page.q);
  const query = params.toString();
  return fetchJSON(`/api/players${query ? `?${query}` : ''}`);
}

export async function fetchPlayerClips(playerId: number, page?: { cursor?: number | null; role?: string; clutch?: boolean }): Promise<PlayerClipPage> {
  const params = new URLSearchParams();
  if (page?.cursor) params.set('cursor', String(page.cursor));
  if (page?.clutch) params.set('clutch', '1');
  if (page?.role) params.set('role', page.role);
  const query = params.toString();
  return fetchJSON(`/api/players/${playerId}/clips${query ? `?${query}` : ''}`);
}

export function playerClipUrl(playerId: number, clipId: number): string {
  return `${BASE}/api/players/${playerId}/clips/${clipId}`;
}


export function fetchTeams(signal?: AbortSignal) {
  return fetchJSON<{ teams: BrowserTeam[] }>('/api/teams', { signal });
}
export function fetchTeamGames(teamId: number, cursor?: number | null, signal?: AbortSignal) {
  return fetchJSON<{ games: TeamGame[]; cursor: number | null }>(`/api/teams/${teamId}/games${cursor ? `?cursor=${cursor}` : ''}`, { signal });
}
export function fetchGameClips(teamId: number, gameId: number, categories: string[], clutch: boolean, cursor?: number | null, signal?: AbortSignal) {
  const params = new URLSearchParams({ scope: 'team', categories: categories.join(',') });
  if (clutch) params.set('clutch', '1');
  if (cursor) params.set('cursor', String(cursor));
  return fetchJSON<GameClipPage>(`/api/teams/${teamId}/games/${gameId}/clips?${params}`, { signal });
}
export function gameClipUrl(teamId: number, gameId: number, clipId: number) {
  return `${BASE}/api/teams/${teamId}/games/${gameId}/clips/${clipId}`;
}
