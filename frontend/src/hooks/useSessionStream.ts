import { useCallback, useEffect, useRef, useState } from "react";
import { sessionSocketUrl } from "../api/client";
import type { OutboundEvent, TranscriptTurn } from "../api/types";

/**
 * Owns the WebSocket connection for one session: sends utterance frames,
 * folds incoming signal/recommendation/guardrail_block events onto the
 * matching transcript turn (matched by exact utterance text -- fine for
 * this demo's non-repeating sample transcript; a production UI would key
 * on a server-assigned per-utterance id instead, see docs/PRODUCTION.md),
 * and exposes plain state + a `send` function to the component tree.
 */
export function useSessionStream(sessionId: string | null) {
  const [turns, setTurns] = useState<TranscriptTurn[]>([]);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    const socket = new WebSocket(sessionSocketUrl(sessionId));
    socketRef.current = socket;

    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as OutboundEvent;
      applyEvent(event, setTurns);
    };

    return () => {
      socket.close();
      socketRef.current = null;
    };
  }, [sessionId]);

  const send = useCallback((speaker: string, text: string, ts: number) => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    setTurns((prev) => [...prev, { id: `${ts}-${speaker}`, speaker, text, ts }]);
    socket.send(JSON.stringify({ speaker, text, ts, is_final: true }));
  }, []);

  return { turns, connected, send };
}

function applyEvent(event: OutboundEvent, setTurns: React.Dispatch<React.SetStateAction<TranscriptTurn[]>>) {
  if (event.type === "error") {
    // eslint-disable-next-line no-console
    console.error("copilot error event:", event.detail);
    return;
  }

  setTurns((prev) => {
    const idx = [...prev].reverse().findIndex((t) => t.text === event.utterance);
    if (idx === -1) return prev;
    const realIdx = prev.length - 1 - idx;
    const next = [...prev];
    const turn = { ...next[realIdx] };
    if (event.type === "signal") turn.signal = event;
    if (event.type === "recommendation") turn.recommendation = event;
    if (event.type === "guardrail_block") turn.guardrailBlock = event;
    next[realIdx] = turn;
    return next;
  });
}
