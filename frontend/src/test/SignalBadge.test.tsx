import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SignalBadge } from "../components/SignalBadge";

describe("SignalBadge", () => {
  it("renders the label text", () => {
    render(<SignalBadge label="OBJECTION" />);
    expect(screen.getByTestId("signal-badge")).toHaveTextContent("OBJECTION");
  });

  it("renders confidence percentage when provided", () => {
    render(<SignalBadge label="BUYING_SIGNAL" confidence={0.67} />);
    expect(screen.getByTestId("signal-badge")).toHaveTextContent("67%");
  });

  it("omits percentage when confidence is not provided", () => {
    render(<SignalBadge label="NEUTRAL" />);
    expect(screen.getByTestId("signal-badge")).not.toHaveTextContent("%");
  });
});
