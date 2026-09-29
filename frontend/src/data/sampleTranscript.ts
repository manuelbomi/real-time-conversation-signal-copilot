// Mirrors backend/scripts/sample_transcript.jsonl so the "Replay a sample
// call" button in the UI works without a separate file fetch. Keep these
// in sync if you edit one -- see docs/PRODUCTION.md for why a demo fixture
// like this is duplicated rather than shared across the frontend/backend
// boundary in a minimal reference repo.
export interface SampleTurn {
  speaker: string;
  text: string;
  delayMs: number;
}

export const SAMPLE_TRANSCRIPT: SampleTurn[] = [
  { speaker: "customer", text: "Hi, I've been looking at your standard account but I'm not sure about the fees.", delayMs: 200 },
  { speaker: "agent", text: "Happy to walk through that. What specifically about the fees concerns you?", delayMs: 1200 },
  { speaker: "customer", text: "Honestly it just feels too expensive compared to what I'm paying now.", delayMs: 1500 },
  { speaker: "customer", text: "Also, can you just guarantee I won't lose any money if I switch?", delayMs: 2000 },
  { speaker: "agent", text: "I understand the concern about cost, let me explain what's included at this tier.", delayMs: 1000 },
  { speaker: "customer", text: "Okay that actually makes sense. How do I get started?", delayMs: 2500 },
  { speaker: "customer", text: "What happens if I want to close the account later?", delayMs: 1500 },
  { speaker: "customer", text: "Great, thanks for explaining.", delayMs: 1000 },
];
