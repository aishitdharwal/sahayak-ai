import { useEffect, useRef, useCallback } from "react";
import { WSEvent } from "../types";

const WS_URL = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/agent`;

export function useAgentSocket(onEvent: (event: WSEvent) => void, onConnect?: () => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const onEventRef = useRef(onEvent);
  const onConnectRef = useRef(onConnect);
  onEventRef.current = onEvent;
  onConnectRef.current = onConnect;

  const connect = useCallback(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data) as WSEvent;
        onEventRef.current(event);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      // Reconnect after 2s if connection drops
      setTimeout(connect, 2000);
    };

    ws.onopen = () => {
      onConnectRef.current?.();
      // Send a ping every 30s to keep the connection alive
      const interval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send("ping");
        else clearInterval(interval);
      }, 30_000);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => wsRef.current?.close();
  }, [connect]);
}
