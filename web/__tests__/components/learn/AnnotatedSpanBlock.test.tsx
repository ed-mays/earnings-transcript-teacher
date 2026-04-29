import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnnotatedSpanBlock } from "@/components/learn/AnnotatedSpanBlock";
import { buildTermRegex } from "@/lib/highlight";
import type { SpanItem, TermDefinition } from "@/components/transcript/types";
import { DEFAULT_LAYERS } from "@/components/learn/types";

const SPAN: SpanItem = {
  speaker: "Jensen Huang",
  section: "qa",
  text: "Our data center GPU business grew sharply this quarter.",
  sequence_order: 42,
};

const TERM: TermDefinition = {
  term: "data center GPU",
  definition: "Specialized compute hardware",
  explanation: "Used primarily for AI training and inference workloads.",
  category: "industry",
};

const TERM_MAP = new Map<string, TermDefinition>([[TERM.term.toLowerCase(), TERM]]);
const TERM_REGEX = buildTermRegex([TERM.term]);

describe("AnnotatedSpanBlock", () => {
  it("renders the speaker label and span text", () => {
    render(
      <AnnotatedSpanBlock
        span={SPAN}
        layers={{ ...DEFAULT_LAYERS, terms: false }}
        termRegex={null}
        termMap={new Map()}
      />,
    );
    expect(screen.getByText("Jensen Huang")).toBeInTheDocument();
    expect(screen.getByText(SPAN.text)).toBeInTheDocument();
  });

  it("highlights matched terms as tooltip triggers when the terms layer is on", () => {
    render(
      <AnnotatedSpanBlock
        span={SPAN}
        layers={DEFAULT_LAYERS}
        termRegex={TERM_REGEX}
        termMap={TERM_MAP}
      />,
    );
    const trigger = screen
      .getAllByText("data center GPU")
      .find((el) => el.getAttribute("data-slot") === "term-trigger");
    expect(trigger).toBeDefined();
    // Must be visibly styled (not the default unstyled inline button) —
    // confirms the green highlight wraps the term text.
    expect(trigger!.className).toMatch(/bg-green/);
    expect(trigger!.className).toMatch(/underline/);
  });
});
