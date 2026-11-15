export interface BrowserPlayer {
  id: number;
  bbref_id: string;
  full_name: string;
  position: string;
  headshot_url: string | null;
  team: string;
  clips: number;
  games: number;
}

export interface PlayerLibrary {
  season: string;
  seasons: string[];
  teams: string[];
  players: BrowserPlayer[];
  cursor: number | null;
  total: number;
}

export interface PlayerClipRole {
  role: string;
  label: string;
}

export interface PlayerClipPage {
  player: string;
  team: string;
  roles: PlayerClipRole[];
  clips: PlayerClip[];
  cursor: number | null;
}

export interface PlayerClip {
  id: number;
  role: string;
  role_label: string;
  description: string;
  period: number;
  game_clock: string;
  duration_label: string;
  video_start_s: number;
  video_end_s: number;
  bbref_id: string;
  game_date: string;
  season: string;
  matchup: string;
}
