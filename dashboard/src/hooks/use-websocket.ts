"use client";

import { useEffect, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<unknown>(null);
  const timerRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    async function checkHealth() {
      try {
        const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(5000) });
        if (res.ok) {
          setConnected(true);
          const data = await res.json().catch(() => null);
          if (data) setLastMessage(data);
        } else {
          setConnected(false);
        }
      } catch {
        setConnected(false);
      }
    }

    checkHealth();
    timerRef.current = setInterval(checkHealth, 10000);

    return () => {
      clearInterval(timerRef.current);
    };
  }, []);

  return { lastMessage, connected };
}
