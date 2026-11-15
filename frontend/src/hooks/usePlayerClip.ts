import { useRef, useState } from 'react';
import { playerClipUrl } from '../api';
import type { PlayerClip } from '../types';

export function usePlayerClip() {
  const [active, setActive] = useState<PlayerClip | null>(null);
  const [url, setUrl] = useState('');
  const [cutting, setCutting] = useState(false);
  const [error, setError] = useState('');
  const urlRef = useRef('');
  const requestId = useRef(0);

  function clear() {
    requestId.current += 1;
    setActive(null);
    setCutting(false);
    setError('');
    urlRef.current = '';
    setUrl('');
  }

  function play(playerId: number, clip: PlayerClip) {
    if (active?.id === clip.id && urlRef.current) {
      setActive(clip);
      return;
    }
    requestId.current += 1;
    setError('');
    setCutting(true);
    setActive(clip);
    const next = playerClipUrl(playerId, clip.id);
    urlRef.current = next;
    setUrl(next);
  }

  function started() {
    setCutting(false);
  }

  function failed() {
    setCutting(false);
    setError('Could not cut this clip.');
    urlRef.current = '';
    setUrl('');
  }

  return { active, url, cutting, error, play, clear, started, failed };
}
