import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useAnnotations } from "@/hooks/useAnnotations";
import { api } from "@/lib/api";
import type { LearnAnnotationsResponse } from "@/components/transcript/types";

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
  },
}));

const getMock = api.get as unknown as ReturnType<typeof vi.fn>;

function makeResponse(
  overrides: Partial<LearnAnnotationsResponse> = {},
): LearnAnnotationsResponse {
  return {
    terms: [],
    evasion: [],
    takeaways: [],
    misconceptions: [],
    synthesis: null,
    ...overrides,
  };
}

describe("useAnnotations", () => {
  beforeEach(() => {
    getMock.mockReset();
  });

  it("fetches and returns annotations on mount", async () => {
    const response = makeResponse({
      terms: [
        {
          term: "ARR",
          definition: "Annual recurring revenue",
          explanation: "",
          category: "industry",
        },
      ],
    });
    getMock.mockResolvedValueOnce(response);

    const { result } = renderHook(() => useAnnotations("NVDA"));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(getMock).toHaveBeenCalledWith("/api/calls/NVDA/learn-annotations");
    expect(result.current.annotations).toEqual(response);
    expect(result.current.error).toBeNull();
    expect(result.current.termMap.get("arr")).toBeDefined();
  });

  it("filters ambiguous lowercase financial words but keeps acronyms and multi-word terms", async () => {
    getMock.mockResolvedValueOnce(
      makeResponse({
        terms: [
          // Ambiguous lowercase single word — filtered out
          { term: "margin", definition: "", explanation: "", category: "financial" },
          // Multi-word financial — kept
          { term: "gross margin", definition: "", explanation: "", category: "financial" },
          // Financial acronym — kept (was the bug: previous rule dropped these)
          { term: "EBITDA", definition: "", explanation: "", category: "financial" },
          { term: "ARR", definition: "", explanation: "", category: "financial" },
          // Industry — always kept regardless of shape
          { term: "yield", definition: "", explanation: "", category: "industry" },
        ],
      }),
    );

    const { result } = renderHook(() => useAnnotations("NVDA"));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.termMap.has("margin")).toBe(false);
    expect(result.current.termMap.has("gross margin")).toBe(true);
    expect(result.current.termMap.has("ebitda")).toBe(true);
    expect(result.current.termMap.has("arr")).toBe(true);
    expect(result.current.termMap.has("yield")).toBe(true); // industry category bypasses filter
    expect(result.current.termRegex).not.toBeNull();
  });

  it("surfaces an error when the fetch fails", async () => {
    getMock.mockRejectedValueOnce(new Error("network down"));

    const { result } = renderHook(() => useAnnotations("NVDA"));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("network down");
    expect(result.current.annotations).toBeNull();
    expect(result.current.termMap.size).toBe(0);
    expect(result.current.termRegex).toBeNull();
  });
});
