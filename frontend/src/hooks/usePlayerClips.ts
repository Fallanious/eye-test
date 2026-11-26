import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchPlayerClips } from '../api';
import type { PlayerClip } from '../types';

export function usePlayerClips(playerId: number, role: string, clutch: boolean) {
  const [clips, setClips] = useState<PlayerClip[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const generation = useRef(0);
  const busy = useRef(false);

  useEffect(() => {
    const token = ++generation.current;
    busy.current = false;
    setLoading(true);
    setLoadingMore(false);
    setCursor(null);
    setClips([]);
    setError('');
    fetchPlayerClips(playerId, { role, clutch }).then(page => {
      if (token !== generation.current) return;
      setClips(page.clips);
      setCursor(page.cursor);
    }).catch(err => {
      if (token === generation.current) setError(err.message || 'Could not load plays.');
    }).finally(() => {
      if (token === generation.current) setLoading(false);
    });
    return () => { generation.current = token + 1; };
  }, [playerId, role, clutch]);

  const loadMore = useCallback(async () => {
    if (cursor == null || busy.current) return;
    const token = generation.current;
    busy.current = true;
    setLoadingMore(true);
    try {
      const page = await fetchPlayerClips(playerId, { role, clutch, cursor });
      if (token !== generation.current) return;
      setClips(previous => [...previous, ...page.clips]);
      setCursor(page.cursor);
    } catch (err) {
      if (token === generation.current) setError(err instanceof Error ? err.message : 'Could not load plays.');
    } finally {
      if (token === generation.current) {
        busy.current = false;
        setLoadingMore(false);
      }
    }
  }, [playerId, role, clutch, cursor]);

  return { clips, loading, loadingMore, hasMore: cursor !== null, error, loadMore };
}
