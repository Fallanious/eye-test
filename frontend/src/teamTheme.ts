import type { CSSProperties } from 'react';

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

export const TEAM_ALIASES: Record<string, string> = { BRK: 'BKN', CHO: 'CHA', PHO: 'PHX' };

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

export function teamName(team: string) {
  return TEAM_NAMES[TEAM_ALIASES[team] || team] || team;
}

export function teamColors(team: string): readonly [string, string, string] {
  return NBA_COLORS[TEAM_ALIASES[team] || team] || ['#242426', '#A68168', '#D8CEC5'];
}

export function cardColors(team: string): CSSProperties {
  const [primary, middle, back] = teamColors(team);
  return {
    '--card-primary': primary,
    '--card-middle': middle,
    '--card-back': back,
  } as CSSProperties;
}

