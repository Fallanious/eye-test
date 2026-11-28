import { useState, type ReactNode } from 'react';

export default function LoadingCrossfade({ ready, preview, children }: { ready: boolean; preview: ReactNode; children: ReactNode }) {
  const [showPreview, setShowPreview] = useState(!ready);
  if (!ready && !showPreview) setShowPreview(true);
  const revealing = ready && showPreview;
  return <div className="loading-crossfade" data-revealing={revealing}>
    {showPreview && <div className="loading-crossfade-preview" aria-hidden={ready}>
      {preview}
    </div>}
    {ready && <div className="loading-crossfade-results" onAnimationEnd={event => {
      if (event.target === event.currentTarget && event.animationName === 'loading-crossfade-in') setShowPreview(false);
    }}>{children}</div>}
  </div>;
}
