export const PLAY_LABELS = {
  all: 'All plays',
  three_pointer: 'Three-pointers',
  dunk: 'Dunks',
  layup: 'Layups',
  shot: 'Shots',
  rebound: 'Rebounds',
  steal: 'Steals',
  block: 'Blocks',
  assist: 'Assists',
  foul: 'Fouls',
  fouled: 'Fouled',
  turnover: 'Turnovers',
  free_throw: 'Free throws',
} as const;

type PlayCategory = Exclude<keyof typeof PLAY_LABELS, 'all'>;

// The APIs support different filter sets, but share their display labels.
const PLAYER_ROLES = ['shot', 'assist', 'rebound', 'block', 'steal', 'foul', 'fouled', 'turnover'] as const satisfies readonly PlayCategory[];
const GAME_CATEGORIES = ['three_pointer', 'dunk', 'layup', 'shot', 'rebound', 'steal', 'block', 'assist', 'foul', 'turnover', 'free_throw'] as const satisfies readonly PlayCategory[];

export const PLAYER_FILTERS = [
  { role: '', label: PLAY_LABELS.all },
  ...PLAYER_ROLES.map(role => ({ role, label: PLAY_LABELS[role] })),
];

export const GAME_FILTERS = GAME_CATEGORIES.map(category => ({ category, label: PLAY_LABELS[category] }));

export function playLabel(category: string): string {
  return Object.hasOwn(PLAY_LABELS, category) ? PLAY_LABELS[category as keyof typeof PLAY_LABELS] : category;
}
