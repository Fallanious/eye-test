import type { CSSProperties } from 'react';

export default function TeamPickerPreview({ filters = false }: { filters?: boolean }) {
  return <div className={filters ? 'pb-team-tabs' : 'tb-team-picker'} role="status" aria-label="Loading teams">
    {Array.from({ length: filters ? 31 : 30 }, (_, index) => (
      <div className="pb-team-tab pb-card" key={index} aria-hidden="true"
        style={{ '--loading-delay': `${index % 6 * 0.12}s` } as CSSProperties}>
        <span className="pb-info"><span className="pb-skeleton pb-skeleton-line team-name-placeholder" /></span>
      </div>
    ))}
  </div>;
}
