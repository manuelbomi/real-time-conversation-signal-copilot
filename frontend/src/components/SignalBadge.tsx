import type { SignalLabel } from "../api/types";

// One color per label so a reviewer can pattern-match the transcript at a
// glance without reading every badge's text -- COMPLIANCE_RISK is red
// deliberately, it's the one label that should draw the eye fastest.
const LABEL_COLORS: Record<SignalLabel, string> = {
  OBJECTION: "#b45309",
  BUYING_SIGNAL: "#15803d",
  COMPLIANCE_RISK: "#b91c1c",
  QUESTION: "#1d4ed8",
  ACTION_ITEM: "#6d28d9",
  NEUTRAL: "#6b7280",
};

interface Props {
  label: SignalLabel;
  confidence?: number;
}

export function SignalBadge({ label, confidence }: Props) {
  const color = LABEL_COLORS[label] ?? "#6b7280";
  const pct = confidence !== undefined ? Math.round(confidence * 100) : undefined;

  return (
    <span
      data-testid="signal-badge"
      style={{
        backgroundColor: color,
        color: "white",
        borderRadius: "999px",
        padding: "2px 10px",
        fontSize: "0.75rem",
        fontWeight: 600,
        marginRight: "6px",
        display: "inline-block",
      }}
      title={pct !== undefined ? `confidence ${pct}%` : undefined}
    >
      {label}
      {pct !== undefined ? ` · ${pct}%` : ""}
    </span>
  );
}
