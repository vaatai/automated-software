"use client";

import { useEffect, useRef, useState } from "react";

function getWsUrl(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
  if (typeof window === "undefined") return "ws://localhost:8000/ws/monitoring";
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws/monitoring`;
}
const WS_URL = getWsUrl();

export function useWebSocket<T = unknown>() {
  const [lastMessage, setLastMessage] = useState<T | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    function connect() {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => setConnected(true);
        ws.onclose = () => {
          setConnected(false);
          reconnectTimer.current = setTimeout(connect, 5000);
        };
        ws.onerror = () => ws.close();
        ws.onmessage = (event) => {
          try {
            setLastMessage(JSON.parse(event.data) as T);
          } catch {
            /* ignore non-JSON */
          }
        };
      } catch {
        reconnectTimer.current = setTimeout(connect, 5000);
      }
    }

    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, []);

  return { lastMessage, connected };
}
