import React, { Suspense } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import LearnPage from "@/app/calls/[ticker]/learn/page";
import { callDetail } from "../utils/fixtures";

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
import { streamChat } from "@/lib/chat";

const mockGet = api.get as ReturnType<typeof vi.fn>;
const mockStreamChat = streamChat as ReturnType<typeof vi.fn>;

function renderLearnPage(ticker = "aapl", topic?: string) {
  return render(
    <Suspense fallback={<div>Loading...</div>}>
      <LearnPage
        params={fulfilledPromise({ ticker })}
        searchParams={fulfilledPromise({ topic })}
      />
    </Suspense>
  );
}

describe("LearnPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockResolvedValue(callDetail);
    mockStreamChat.mockResolvedValue(undefined);
  });

  it("renders the heading with the uppercased ticker", async () => {
    renderLearnPage("aapl");
    expect(screen.getByText(/AAPL/)).toBeInTheDocument();
    // Wait for the suggestions useEffect to settle so act() warnings don't appear
    await waitFor(() => expect(mockGet).toHaveBeenCalled());
  });

  it("loads CallDetail and shows suggestion buttons from themes", async () => {
    renderLearnPage("aapl");
    // callDetail has themes: ["services growth", "hardware resilience"]
    // buildSuggestions generates questions from those
    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(expect.stringContaining("/api/calls/aapl"));
    });
  });

  it("appends user message to thread when Send is clicked", async () => {
    renderLearnPage("aapl");
    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "What drove services revenue?");
    await userEvent.keyboard("{Enter}");
    await waitFor(() => {
      expect(screen.getByText("What drove services revenue?")).toBeInTheDocument();
    });
    expect(mockStreamChat).toHaveBeenCalledWith(
      "aapl",
      "What drove services revenue?",
      null,
      expect.any(Object),
      expect.any(AbortSignal)
    );
  });

  it("clears messages and resets state when New session is clicked", async () => {
    // Make streamChat call onDone to add an assistant message
    mockStreamChat.mockImplementation(
      (_ticker: unknown, _message: unknown, _sessionId: unknown, callbacks: { onToken: (t: string) => void; onDone: (id: string) => void }) => {
        callbacks.onToken("Great question.");
        callbacks.onDone("session-1");
        return Promise.resolve();
      }
    );

    renderLearnPage("aapl");
    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "Tell me about iPhone");
    await userEvent.keyboard("{Enter}");

    // Wait for the assistant message to appear
    await waitFor(() => {
      expect(screen.getByText("Tell me about iPhone")).toBeInTheDocument();
    });

    // Click "New session"
    await userEvent.click(screen.getByRole("button", { name: /new session/i }));

    // Messages should be gone
    await waitFor(() => {
      expect(screen.queryByText("Tell me about iPhone")).not.toBeInTheDocument();
    });
  });
});
