import type { GuardrailBlockEvent, RecommendationEvent } from "../api/types";

interface Props {
  recommendation?: RecommendationEvent;
  guardrailBlock?: GuardrailBlockEvent;
}

/**
 * Renders exactly one of: a grounded recommendation with its citations, or
 * a guardrail-block notice. Never both, and never a "cleaned up" version of
 * a blocked recommendation -- a blocked recommendation is never shown, per
 * the withhold-not-rewrite guardrail policy (see backend
 * app/guardrails/compliance.py).
 */
export function RecommendationPanel({ recommendation, guardrailBlock }: Props) {
  if (guardrailBlock) {
    return (
      <div data-testid="guardrail-block" style={panelStyle("#fef2f2", "#b91c1c")}>
        <strong>Recommendation withheld</strong>
        <p style={{ margin: "4px 0 0" }}>{guardrailBlock.reason}</p>
        <small>blocked by: {guardrailBlock.blocked_by}</small>
      </div>
    );
  }

  if (recommendation) {
    return (
      <div data-testid="recommendation" style={panelStyle("#f0fdf4", "#15803d")}>
        <p style={{ margin: 0 }}>{recommendation.text}</p>
        {recommendation.citations.length > 0 && (
          <ul style={{ margin: "6px 0 0", paddingLeft: "18px", fontSize: "0.8rem", color: "#374151" }}>
            {recommendation.citations.map((citation) => (
              <li key={citation}>{citation}</li>
            ))}
          </ul>
        )}
        {!recommendation.is_grounded && <small style={{ color: "#b45309" }}>ungrounded -- no matching reference found</small>}
      </div>
    );
  }

  return null;
}

function panelStyle(bg: string, border: string): React.CSSProperties {
  return {
    background: bg,
    border: `1px solid ${border}`,
    borderRadius: "8px",
    padding: "8px 12px",
    marginTop: "6px",
  };
}
