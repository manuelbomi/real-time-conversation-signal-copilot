import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TranscriptView } from "../components/TranscriptView";
import type { TranscriptTurn } from "../api/types";

describe("TranscriptView", () => {
  it("shows an empty-state message with no turns", () => {
    render(<TranscriptView turns={[]} />);
    expect(screen.getByText(/No turns yet/)).toBeInTheDocument();
  });

  it("renders each turn's speaker and text", () => {
    const turns: TranscriptTurn[] = [
      { id: "1", speaker: "customer", text: "This is too expensive.", ts: 0 },
      { id: "2", speaker: "agent", text: "Let's talk about that.", ts: 1 },
    ];
    render(<TranscriptView turns={turns} />);
    expect(screen.getByText(/This is too expensive/)).toBeInTheDocument();
    expect(screen.getByText(/Let's talk about that/)).toBeInTheDocument();
  });

  it("renders signal badges attached to a turn", () => {
    const turns: TranscriptTurn[] = [
      {
        id: "1",
        speaker: "customer",
        text: "too expensive",
        ts: 0,
        signal: {
          type: "signal",
          utterance: "too expensive",
          speaker: "customer",
          labels: ["OBJECTION"],
          confidence: { OBJECTION: 1.0 },
          rationale: "price concern",
        },
      },
    ];
    render(<TranscriptView turns={turns} />);
    expect(screen.getByTestId("signal-badge")).toHaveTextContent("OBJECTION");
  });
});
