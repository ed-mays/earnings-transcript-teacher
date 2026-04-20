import { describe, it, expect } from "vitest";
import {
  buildTermRegex,
  findEvasionSpanIndex,
  highlightTerms,
  normalizeForMatch,
  type SpanItem,
  type TermDefinition,
} from "@/lib/highlight";

function makeTermMap(terms: TermDefinition[]): Map<string, TermDefinition> {
  return new Map(terms.map((t) => [t.term.toLowerCase(), t]));
}

function makeDef(term: string, category: "industry" | "financial" = "industry"): TermDefinition {
  return { term, definition: `${term} def`, explanation: `${term} expl`, category };
}

const renderMarker = (matched: string, _def: TermDefinition, key: string) =>
  `<<${key}:${matched}>>`;

describe("buildTermRegex", () => {
  it("returns null for empty list", () => {
    expect(buildTermRegex([])).toBeNull();
  });

  it("escapes regex special characters", () => {
    const rx = buildTermRegex(["S&P 500", "10-K"]);
    expect(rx).not.toBeNull();
    expect(rx!.test("The S&P 500 closed up.")).toBe(true);
    expect(rx!.test("Filed their 10-K.")).toBe(true);
  });

  it("orders longer terms first so alternation prefers them", () => {
    const rx = buildTermRegex(["margin", "gross margin"])!;
    const match = "gross margin expanded".match(rx);
    expect(match?.[0].toLowerCase()).toBe("gross margin");
  });
});

describe("normalizeForMatch", () => {
  it("collapses whitespace and newlines to single spaces", () => {
    expect(normalizeForMatch("  hello\n  world  ")).toBe("hello world");
  });

  it("lowercases input", () => {
    expect(normalizeForMatch("Hello World")).toBe("hello world");
  });
});

describe("highlightTerms", () => {
  it("wraps a matched term with the renderer", () => {
    const terms = [makeDef("EBITDA", "financial")];
    const rx = buildTermRegex(terms.map((t) => t.term));
    const nodes = highlightTerms("The EBITDA grew 15%", rx, makeTermMap(terms), renderMarker);
    expect(nodes).toEqual(["The ", "<<term-0:EBITDA>>", " grew 15%"]);
  });

  it("matches case-insensitively", () => {
    const terms = [makeDef("EBITDA", "financial")];
    const rx = buildTermRegex(terms.map((t) => t.term));
    const nodes = highlightTerms("ebitda grew", rx, makeTermMap(terms), renderMarker);
    expect(nodes[0]).toBe("<<term-0:ebitda>>");
  });

  it("returns text unchanged when regex is null", () => {
    const nodes = highlightTerms("no terms here", null, new Map(), renderMarker);
    expect(nodes).toEqual(["no terms here"]);
  });

  it("handles multiple non-overlapping matches", () => {
    const terms = [makeDef("ARR", "financial"), makeDef("EBITDA", "financial")];
    const rx = buildTermRegex(terms.map((t) => t.term));
    const nodes = highlightTerms(
      "ARR and EBITDA both rose",
      rx,
      makeTermMap(terms),
      renderMarker,
    );
    expect(nodes).toEqual([
      "<<term-0:ARR>>",
      " and ",
      "<<term-1:EBITDA>>",
      " both rose",
    ]);
  });
});

describe("findEvasionSpanIndex", () => {
  it("returns the index of the span containing the normalized answer", () => {
    const spans: SpanItem[] = [
      { speaker: "CEO", section: "qa", text: "We are investing in growth.", sequence_order: 1 },
      {
        speaker: "CEO",
        section: "qa",
        text: "  Gross margin compression reflects capacity ramp during this period.",
        sequence_order: 2,
      },
    ];
    const answer = "Gross margin compression reflects capacity ramp during this period.";
    expect(findEvasionSpanIndex(answer, spans)).toBe(1);
  });

  it("returns null when no span matches", () => {
    const spans: SpanItem[] = [
      { speaker: "CEO", section: "qa", text: "Totally unrelated answer.", sequence_order: 1 },
    ];
    expect(findEvasionSpanIndex("we expect higher guidance next quarter", spans)).toBeNull();
  });

  it("returns null for empty answer", () => {
    expect(findEvasionSpanIndex("", [])).toBeNull();
  });
});
