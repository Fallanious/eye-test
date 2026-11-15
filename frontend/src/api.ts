import type { PlayerLibrary, PlayerClipPage } from "./types";
const BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/$/, '');
async function fetchJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, init);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

async function fetchBlob(url: string, init?: RequestInit): Promise<Blob> {
  const res = await fetch(`${BASE}${url}`, init);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || `Request failed (${res.status})`);
  }
  return res.blob();
}

export async function fetchPlayerLibrary(page?: { cursor?: number | null; team?: string; q?: string }): Promise<PlayerLibrary> {
  const params = new URLSearchParams();
  if (page?.cursor) params.set('cursor', String(page.cursor));
  if (page?.team) params.set('team', page.team);
  if (page?.q) params.set('q', page.q);
  const query = params.toString();
  return fetchJSON(`/api/players${query ? `?${query}` : ''}`);
}

export async function fetchPlayerClips(playerId: number, page?: { cursor?: number | null; role?: string }): Promise<PlayerClipPage> {
  const params = new URLSearchParams();
  if (page?.cursor) params.set('cursor', String(page.cursor));
  if (page?.role) params.set('role', page.role);
  const query = params.toString();
  return fetchJSON(`/api/players/${playerId}/clips${query ? `?${query}` : ''}`);
}

export async function fetchPlayerClip(playerId: number, clipId: number): Promise<Blob> {
  return fetchBlob(`/api/players/${playerId}/clips/${clipId}`);
}

