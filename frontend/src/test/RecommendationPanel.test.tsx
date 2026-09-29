import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RecommendationPanel } from "../components/RecommendationPanel";

describe("RecommendationPanel", () => {
  it("renders nothing when neither prop is provided", () => {
    const { container } = render(<RecommendationPanel />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders a grounded recommendation with citations", () => {
    render(
      <RecommendationPanel
        recommendation={{
          type: "recommendation",
          utterance: "too expensive",
          text: "Acknowledge the concern and explain what's included.",
          citations: ["01-objection-handling.md § Price concerns"],
          is_grounded: true,
        }}
      />,
    );
    expect(screen.getByTestId("recommendation")).toHaveTextContent("Acknowledge the concern");
    expect(screen.getByText(/Price concerns/)).toBeInTheDocument();
  });

  it("renders a guardrail block instead of the recommendation when both could apply", () => {
    render(
      <RecommendationPanel
        recommendation={{
          type: "recommendation",
          utterance: "guarantee",
          text: "should not be shown",
          citations: [],
          is_grounded: false,
        }}
        guardrailBlock={{
          type: "guardrail_block",
          utterance: "guarantee",
          reason: "contains an absolute guarantee-style claim",
          blocked_by: "blocklist",
        }}
      />,
    );
    expect(screen.getByTestId("guardrail-block")).toHaveTextContent("Recommendation withheld");
    expect(screen.queryByTestId("recommendation")).not.toBeInTheDocument();
  });
});
