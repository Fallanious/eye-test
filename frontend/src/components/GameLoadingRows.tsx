import type { CSSProperties } from 'react';
import ClipStack from './ClipStack';

function TeamPlaceholder() {
  return <span className="games-team">
    <ClipStack className="pb-team-mark" />
    <span className="pb-skeleton-line games-name-placeholder" />
  </span>;
}

export default function GameLoadingRows({ count = 3, matchup = false }: { count?: number; matchup?: boolean }) {
  return <div role="status" aria-label={count === 1 ? 'Loading game' : 'Loading games'}>
    {Array.from({ length: count }, (_, index) => (
      <div key={index} className={'tb-game-card ' + (matchup ? 'games-matchup games-placeholder' : 'tb-game-skeleton')} aria-hidden="true"
        style={{ '--loading-delay': `${index * 0.12}s` } as CSSProperties}>
        {matchup ? <>
          <span className="games-matchup-info pb-loading-fade">
            <span className="games-opponents"><TeamPlaceholder /><span className="games-at">at</span><TeamPlaceholder /></span>
            <small className="pb-skeleton-line games-time-placeholder" />
          </span>
          <span className="games-status pb-loading-fade"><span className="pb-skeleton-line games-status-placeholder" /></span>
        </> : <>
          <span className="pb-skeleton pb-skeleton-line" />
          <span className="pb-skeleton pb-skeleton-line short" />
        </>}
      </div>
    ))}
  </div>;
}
