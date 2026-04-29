import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { GuidedAnalysisView } from "@/app/calls/[ticker]/GuidedAnalysisView";
import { callDetail, spansResponse } from "../utils/fixtures";
import type { LearnAnnotationsResponse } from "@/components/transcript/types";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock("@/lib/chat", () => ({
  streamChat: vi.fn(),
}));

import { api } from "@/lib/api";

const mockGet = api.get as ReturnType<typeof vi.fn>;

const emptyAnnotations: LearnAnnotationsResponse = {
  terms: [],
  evasion: [],
  takeaways: [],
  misconceptions: [],
  synthesis: null,
};

function setupApiResponses(
  overrides: Partial<{ annotations: LearnAnnotationsResponse }> = {},
) {
  mockGet.mockImplementation((path: string) => {
    if (path.includes("/learn-annotations")) {
      return Promise.resolve(overrides.annotations ?? emptyAnnotations);
    }
    if (path.includes("/spans")) {
      return Promise.resolve(spansResponse);
    }
    return Promise.resolve(callDetail);
  });
}

function renderGuided(topic?: string) {
  return render(
    <GuidedAnalysisView
      call={callDetail}
      adjacent={{ prev: null, next: null }}
      initialTopic={topic}
    />,
  );
}

describe("GuidedAnalysisView", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupApiResponses();
  });

  it("renders the Guided Analysis heading with the uppercased ticker", async () => {
    renderGuided();
    const heading = screen.getByRole("heading", { name: /AAPL/ });
    expect(heading).toHaveTextContent(/AAPL/);
    expect(heading).toHaveTextContent(/Guided Analysis/);
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
  });

  it("fetches learn-annotations and spans on mount", async () => {
    renderGuided();
    await waitFor(() => {
      const paths = mockGet.mock.calls.map(([p]) => p as string);
      expect(paths.some((p) => p.includes("/learn-annotations"))).toBe(true);
      expect(paths.some((p) => p.includes("/spans"))).toBe(true);
    });
  });

  it("renders the three annotation layer switches", async () => {
    // Evasion was retired in PR #421 — Q&A Forensics now owns that surface.
    renderGuided();
    await waitFor(() => {
      expect(screen.getByRole("switch", { name: /Guidance/i })).toBeInTheDocument();
      expect(screen.getByRole("switch", { name: /Sentiment/i })).toBeInTheDocument();
      expect(screen.getByRole("switch", { name: /Terms/i })).toBeInTheDocument();
      expect(screen.queryByRole("switch", { name: /Evasion/i })).not.toBeInTheDocument();
    });
  });

  it("opens the chat panel when 'Explore with Feynman' is clicked", async () => {
    renderGuided();
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    await userEvent.click(screen.getByRole("button", { name: /Explore with Feynman/i }));
    expect(
      screen.getByRole("complementary", { name: /Learning chat/i }),
    ).toBeInTheDocument();
  });

  it("pre-opens the chat panel when initialTopic is supplied", async () => {
    renderGuided("EBITDA");
    await waitFor(() => {
      expect(
        screen.getByRole("complementary", { name: /Learning chat/i }),
      ).toBeInTheDocument();
    });
  });
});
