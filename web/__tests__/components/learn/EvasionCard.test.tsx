import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { EvasionCard } from "@/components/learn/EvasionCard";
import type { QAEvasionItem } from "@/components/transcript/types";

const SAMPLE: QAEvasionItem = {
  analyst_name: "Jane Doe",
  question_topic: "Gross margin",
  question_text: "Why did margin compress?",
  answer_text: "We're investing in capacity for growth.",
  analyst_concern: "Dodged the margin question",
  defensiveness_score: 7,
  evasion_explanation: "Deflected to a growth narrative instead of addressing margin.",
};

describe("EvasionCard", () => {
  it("renders analyst concern, evasion tag, and defensiveness detail by default", () => {
    render(<EvasionCard item={SAMPLE} onChatClick={() => {}} />);
    expect(screen.getByText("Dodged the margin question")).toBeInTheDocument();
    // Primary framing: "Evasion · [Level]"
    expect(screen.getByText(/Evasion · Medium/i)).toBeInTheDocument();
    // Numeric score demoted to secondary metadata
    expect(screen.getByText(/defensiveness 7\/10/)).toBeInTheDocument();
    expect(screen.getByText(/Jane Doe/)).toBeInTheDocument();
  });

  it("invokes onChatClick with an evasion context when the chat icon is clicked", async () => {
    const onChatClick = vi.fn();
    render(<EvasionCard item={SAMPLE} onChatClick={onChatClick} />);
    await userEvent.click(screen.getByRole("button", { name: /Discuss this evasion/i }));
    expect(onChatClick).toHaveBeenCalledWith({
      type: "evasion",
      text: SAMPLE.answer_text,
      metadata: SAMPLE.analyst_concern,
    });
  });
});
