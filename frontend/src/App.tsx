import { useEffect, useState } from "react";
import { createSession } from "./api/client";
import { ReplayControl } from "./components/ReplayControl";
import { TranscriptView } from "./components/TranscriptView";
import { useSessionStream } from "./hooks/useSessionStream";

export function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const { turns, connected, send } = useSessionStream(sessionId);

  useEffect(() => {
    createSession().then(setSessionId).catch(console.error);
  }, []);

  return (
    <div style={{ maxWidth: "760px", margin: "0 auto", padding: "24px", fontFamily: "system-ui, sans-serif" }}>
      <h1 style={{ fontSize: "1.4rem" }}>Real-Time Conversation Signal Copilot</h1>
      <p style={{ color: "#6b7280" }}>
        {sessionId ? `session ${sessionId.slice(0, 8)} — ${connected ? "connected" : "connecting..."}` : "starting session..."}
      </p>
      <ReplayControl connected={connected} onSend={send} />
      <div style={{ marginTop: "20px" }}>
        <TranscriptView turns={turns} />
      </div>
    </div>
  );
}
