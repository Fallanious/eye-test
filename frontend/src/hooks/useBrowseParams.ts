import { useSearchParams } from 'react-router';

export function useBrowseParams() {
  const [params, setParams] = useSearchParams();

  function update(values: Record<string, string | string[]>, replace = false) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(values)) {
      next.delete(key);
      for (const item of Array.isArray(value) ? value : [value]) {
        if (item) next.append(key, item);
      }
    }
    if (next.toString() !== params.toString()) setParams(next, { replace });
  }

  return { params, update };
}

export function positiveId(value: string | null | undefined) {
  if (!value || !/^\d+$/.test(value)) return null;
  const id = Number(value);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}
