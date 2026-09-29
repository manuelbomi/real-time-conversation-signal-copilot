import type { TranscriptTurn } from "../api/types";
import { RecommendationPanel } from "./RecommendationPanel";
import { SignalBadge } from "./SignalBadge";

interface Props {
  turns: TranscriptTurn[];
}

export function TranscriptView({ turns }: Props) {
  if (turns.length === 0) {
    return <p style={{ color: "#6b7280" }}>No turns yet -- start a replay or connect a live source.</p>;
  }

  return (
    <div data-testid="transcript-view">
      {turns.map((turn) => (
        <div key={turn.id} style={{ marginBottom: "14px", paddingBottom: "10px", borderBottom: "1px solid #e5e7eb" }}>
          <div>
            <strong>{turn.speaker}:</strong> {turn.text}
          </div>
          {turn.signal && (
            <div style={{ marginTop: "4px" }}>
              {turn.signal.labels.map((label) => (
                <SignalBadge key={label} label={label} confidence={turn.signal!.confidence[label]} />
              ))}
            </div>
          )}
          <RecommendationPanel recommendation={turn.recommendation} guardrailBlock={turn.guardrailBlock} />
        </div>
      ))}
    </div>
  );
}
