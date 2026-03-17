import { useState } from 'react';

const KEY = 'deviation_cliproxy_enabled';

export function useCLIProxyEnabled(): [boolean, (v: boolean) => void] {
  const [enabled, setEnabledState] = useState<boolean>(() => {
    try {
      return localStorage.getItem(KEY) === 'true';
    } catch {
      return false;
    }
  });

  const setEnabled = (v: boolean) => {
    try {
      localStorage.setItem(KEY, String(v));
    } catch {}
    setEnabledState(v);
  };

  return [enabled, setEnabled];
}
