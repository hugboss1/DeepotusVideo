import { useEffect, useRef, useState } from "react";

// useState that mirrors to localStorage so in-progress work (a template
// being built for a post, filled slot inputs, a generated script) survives
// edit<->render toggles, provider-tab switches and full page reloads.
export function usePersistedState(key, initial) {
  const [value, setValue] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw != null) return JSON.parse(raw);
    } catch {
      /* ignore corrupt/blocked storage */
    }
    return typeof initial === "function" ? initial() : initial;
  });

  const keyRef = useRef(key);
  useEffect(() => {
    keyRef.current = key;
    // re-hydrate if the key changes (e.g. switching template id)
    try {
      const raw = localStorage.getItem(key);
      if (raw != null) setValue(JSON.parse(raw));
    } catch {
      /* ignore */
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    try {
      localStorage.setItem(keyRef.current, JSON.stringify(value));
    } catch {
      /* storage full / disabled — non-fatal */
    }
  }, [value]);

  return [value, setValue];
}
