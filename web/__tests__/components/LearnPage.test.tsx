import React, { Suspense } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import LearnPage from "@/app/calls/[ticker]/learn/page";
import { callDetail, spansResponse } from "../utils/fixtures";
import type { LearnAnnotationsResponse } from "@/components/transcript/types";

/**
 * React 19's use() hook checks promise.status === "fulfilled" to return
 * synchronously without suspending. Pre-set these fields so the component
 * renders immediately in tests without needing a Suspense cycle.
 */
function fulfilledPromise<T>(value: T): Promise<T> {
  const p = Promise.resolve(value) as Promise<T> & {
    status?: string;
    value?: T;
  };
  p.status = "fulfilled";
  p.value = value;
  return p;
}

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

function setupApiResponses(overrides: Partial<{ annotations: LearnAnnotationsResponse }> = {}) {
  mockGet.mockImplementation((path: string) => {
    if (path.includes("/learn-annotations")) {
      return Promise.resolve(overrides.annotations ?? emptyAnnotations);
    }
    if (path.includes("/spans")) {
      return Promise.resolve(spansResponse);
    }
    // /api/calls/{ticker}
    return Promise.resolve(callDetail);
  });
}

function renderLearnPage(ticker = "aapl", topic?: string) {
  return render(
    <Suspense fallback={<div>Loading...</div>}>
      <LearnPage
        params={fulfilledPromise({ ticker })}
        searchParams={fulfilledPromise({ topic })}
      />
    </Suspense>,
  );
}

describe("LearnPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupApiResponses();
  });

  it("renders the heading with the uppercased ticker", async () => {
    renderLearnPage("aapl");
    expect(screen.getByRole("heading", { name: /Learn:/i })).toHaveTextContent(/AAPL/);
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
  });

  it("fetches learn-annotations, spans, and call detail on mount", async () => {
    renderLearnPage("aapl");
    await waitFor(() => {
      const paths = mockGet.mock.calls.map(([p]) => p as string);
      expect(paths.some((p) => p.includes("/learn-annotations"))).toBe(true);
      expect(paths.some((p) => p.includes("/spans"))).toBe(true);
      expect(paths.some((p) => p === "/api/calls/aapl")).toBe(true);
    });
  });

  it("renders all four annotation layer switches", async () => {
    renderLearnPage("aapl");
    await waitFor(() => {
      expect(screen.getByRole("switch", { name: /Guidance/i })).toBeInTheDocument();
      expect(screen.getByRole("switch", { name: /Evasion/i })).toBeInTheDocument();
      expect(screen.getByRole("switch", { name: /Sentiment/i })).toBeInTheDocument();
      expect(screen.getByRole("switch", { name: /Terms/i })).toBeInTheDocument();
    });
  });

  it("opens the chat panel when the Discuss button is clicked", async () => {
    renderLearnPage("aapl");
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
    await userEvent.click(screen.getByRole("button", { name: /Discuss/i }));
    expect(screen.getByRole("complementary", { name: /Learning chat/i })).toBeInTheDocument();
  });

  it("pre-opens the chat panel when a ?topic= search param is supplied", async () => {
    renderLearnPage("aapl", "EBITDA");
    await waitFor(() => {
      expect(screen.getByRole("complementary", { name: /Learning chat/i })).toBeInTheDocument();
    });
  });
});
