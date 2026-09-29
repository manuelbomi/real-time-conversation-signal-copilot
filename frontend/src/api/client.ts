const HTTP_BASE = import.meta.env.VITE_API_HTTP_URL ?? "http://localhost:8000";
const WS_BASE = import.meta.env.VITE_API_WS_URL ?? "ws://localhost:8000";

export async function createSession(): Promise<string> {
  const response = await fetch(`${HTTP_BASE}/sessions`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`failed to create session: ${response.status}`);
  }
  const body = (await response.json()) as { session_id: string };
  return body.session_id;
}

export function sessionSocketUrl(sessionId: string): string {
  return `${WS_BASE}/ws/sessions/${sessionId}`;
}
